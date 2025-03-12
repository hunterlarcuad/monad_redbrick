# Monad
Daily Check-In
https://redbrick.land/web3-portal?tab=monad_testnet

# venv
```
# Create venv
python3 -m venv venv
# Activate venv
source venv/bin/activate
# Exit venv
deactivate
```

# Install
```
pip install --upgrade pip
pip install -r requirements.txt
```

# Run
```
cd monad_mint/
cp conf.py.sample conf.py
cp datas/purse/purse.csv.sample datas/purse/purse.csv
# modify datas/purse/purse.csv
python monad_mint.py
```
