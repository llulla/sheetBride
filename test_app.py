import openpyxl

from core import ws_to_tsv


def test_ws_to_tsv():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["a", None, 3])
    ws.append(["b", "c", ""])
    assert ws_to_tsv(ws) == "a\t\t3\nb\tc\t"
    print("ok")


if __name__ == "__main__":
    test_ws_to_tsv()
