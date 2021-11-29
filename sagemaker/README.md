# 【sagemaker】のREADME

## ファイルについて

| ファイル名 | 説明 |
| ---- | ---- |
| model_test_from_learn.py | 着順予想するSageMakerのPythonファイル |
| RaceResultTable_latest.csv | 推論実行用の競馬データ |
| RacePredictedTable.csv | 推論実行結果の競馬データ |


## ワークフロー

EC２で競馬データスクレイピング&データベース更新（keiba_create.py）  
          ↓  
EC２で推論実行用の競馬データを作成&S3にアップロード（keiba2learn.py）  
          ↓  
SageMakerで競馬レースの着順予想の推論を実行S3にアップロード（model_test_from_learn.py）  
          ↓  
推論結果をS3からEC2にダウンロード&データベース更新（keiba2learn.py）  


## model_test_from_learn.py 実行結果例

-----------------------------------------------------------------------------------------

■ SageMakerの「RaceLearnTable_latest.csv」からS3に「RaceLearnTable.csv」としてダウンロードしました

100 200 300 400 500 600 700 800 900 1000 1100 1200 1300 1400 1500 1600 1700 1800 1900 2000 2100 2200 2300 2400 2500 2600 2700 2800 2900 3000 3100 3200 3300 3400 3500 3600 

■ 推論所要時間[sec]： 67.6635947227478, 件数：　3641

■ レースの推論結果をCSV（RacePredictedTable.csv）に出力しました

■ SageMakerの「RacePredictedTable.csv」からS3に「RacePredictedTable.csv」としてアップロードしました

-----------------------------------------------------------------------------------------
