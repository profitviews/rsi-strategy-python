# Documentation

You may need to modify the following setup instructions depending on your operating system. 

1. Ensure Python 3.7 is installed - note websockets is not currently supported with SocketIO on 3.8

2. Create a working directory to clone this repo into

```
mkdir ~/projects/trading/algo
cd ~/projects/trading/algo
```

3. Create a Python 3.7 [virtual environment](https://docs.python.org/3/tutorial/venv.html) and activate it

```
virtualenv -p python3.7 venv
source venv/bin/activate
```

4. Clone this repository

``` 
git clone https://github.com/profitviews/rsi-strategy-python.git
```

5. Navigate to the repo and install all the requirements

```
cd rsi-strategy-python
pip install -r requirements.txt
```

6. Get your ProfitView API key from your [account settings](https://profitview.net/app/settings/account)

![](https://cloud.profitview.net/misc/profitview-api-key.png)

7. Replace `PV_KEY` with your API key in `demo.py` and run to see start streaming realtime trades from BitMEX

```
python demo.py
```

![](https://cloud.profitview.net/misc/stream-bitmex-trades.gif)


