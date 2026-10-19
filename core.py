import json
import os
import shutil
import sys
import tempfile
import time
from datetime import datetime

import openpyxl
import pyperclip
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

APP_DIR = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
CONFIG_PATH = os.path.join(APP_DIR, "config.json")

INTERVALS = {"10분마다": 10, "30분마다": 30, "1시간마다": 60, "수동": 0}

# ponytail: these element locators depend on Google Sheets' undocumented internal DOM
# and can break if Google changes the UI. If pasting stops working, re-inspect the
# page in Chrome devtools and update NAME_BOX / TAB_NAME / ADD_SHEET_BTN below.
NAME_BOX = (By.ID, "t-name-box")
TAB_NAME = (By.CLASS_NAME, "docs-sheet-tab-name")
ADD_SHEET_BTN = (By.CLASS_NAME, "docs-sheet-add-button")
GRID_CONTAINER = (By.ID, "waffle-grid-container")


def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def ws_to_tsv(ws):
    lines = []
    for row in ws.iter_rows():
        lines.append("\t".join("" if c.value is None else str(c.value) for c in row))
    return "\n".join(lines)


def _goto_cell(driver, ref):
    box = driver.find_element(*NAME_BOX)
    box.click()
    box.send_keys(Keys.CONTROL, "a")
    box.send_keys(ref, Keys.ENTER)
    time.sleep(0.3)


def _select_tab(driver, title):
    for tab in driver.find_elements(*TAB_NAME):
        if tab.text.strip() == title:
            tab.click()
            time.sleep(0.5)
            return
    driver.find_element(*ADD_SHEET_BTN).click()
    time.sleep(1)
    new_tab = driver.find_elements(*TAB_NAME)[-1]
    ActionChains(driver).double_click(new_tab).perform()
    time.sleep(0.3)
    new_tab.send_keys(Keys.CONTROL, "a")
    new_tab.send_keys(title, Keys.ENTER)
    time.sleep(0.5)


def _paste_sheet(driver, tsv):
    # A1:ZZ2000-style name-box ranges now error out ("참조된 범위가 시트 크기를
    # 초과합니다") when they exceed the sheet's current grid size, so clear via
    # a real select-all on the grid instead of an oversized name-box range.
    grid = driver.find_element(*GRID_CONTAINER)
    ActionChains(driver).move_to_element(grid).click().perform()
    time.sleep(0.2)
    ActionChains(driver).key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).perform()
    ActionChains(driver).send_keys(Keys.DELETE).perform()
    time.sleep(0.3)
    _goto_cell(driver, "A1")
    pyperclip.copy(tsv)
    ActionChains(driver).key_down(Keys.CONTROL).send_keys("v").key_up(Keys.CONTROL).perform()
    time.sleep(1)


def sync_once(excel_path, sheet_url, log):
    profile_dir = tempfile.mkdtemp(prefix="sheetbride_")
    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--disable-notifications")
    options.add_argument("--window-size=1280,900")
    driver = webdriver.Chrome(options=options)
    try:
        driver.get(sheet_url)
        WebDriverWait(driver, 20).until(EC.presence_of_element_located(NAME_BOX))
        time.sleep(1)
        wb = openpyxl.load_workbook(excel_path, data_only=True)
        for ws in wb.worksheets:
            _select_tab(driver, ws.title)
            _paste_sheet(driver, ws_to_tsv(ws))
        log(f"[{datetime.now():%H:%M:%S}] 동기화 완료 ({len(wb.worksheets)}개 시트)")
    finally:
        driver.quit()
        shutil.rmtree(profile_dir, ignore_errors=True)
