@echo off
setlocal
py -3.12 -c "import numpy,pandas,sklearn,xgboost; print('numpy',numpy.__version__); print('pandas',pandas.__version__); print('scikit-learn',sklearn.__version__); print('xgboost',xgboost.__version__)"
exit /b %ERRORLEVEL%
