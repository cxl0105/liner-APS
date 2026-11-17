# liner-APS

一个用于直线电机型材生产排产的应用程序。

## 本地运行

需要 Python 3.10 或更高版本。安装依赖并启动 Streamlit：

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

## 部署到 Streamlit Community Cloud

1. 将本仓库推送到 GitHub。
2. 在 [Streamlit Community Cloud](https://share.streamlit.io/) 中创建应用，选择本仓库及分支。
3. 将主文件路径设为 `app.py`，然后部署。平台会根据 `requirements.txt` 安装依赖。
