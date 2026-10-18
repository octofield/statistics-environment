# data/

考試給的資料檔（.xlsx / .csv）放這裡。

先看檔案裡有什麼（工作表、欄位、缺值、前幾列，並印出讀檔程式碼）：

```python
df = sk.peek("../data/檔名.xlsx")
```

在 `exam/` 裡的 notebook 讀檔：

```python
df = pd.read_excel("../data/檔名.xlsx", sheet_name="工作表名稱")
df = pd.read_csv("../data/檔名.csv")
```

不知道有哪些工作表：`pd.ExcelFile("../data/檔名.xlsx").sheet_names`

讀進來之後的檢查與整理步驟（型態、缺值、重複、欄位名稱、篩選、分組統計、常見陷阱）：
`notes/00_讀入資料與整理.ipynb`
