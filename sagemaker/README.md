# 【sagemaker】のREADME

## ファイルの説明

| ファイル名 | 説明 |
| ---- | ---- |
| model_test_from_learn.py | 着順予想するSageMakerのPythonファイル |
| RaceResultTable_latest.csv | 推論実行用の競馬データ |
| RacePredictedTable.csv | 推論実行結果の競馬データ |


## model_test_from_learn.py 実行例

-----------------------------------------------------------------------------------------

■ SageMakerの「RaceLearnTable_latest.csv」からS3に「RaceLearnTable.csv」としてダウンロードしました

100 200 300 400 500 600 700 800 900 1000 1100 1200 1300 1400 1500 1600 1700 1800 1900 2000 2100 2200 2300 2400 2500 2600 2700 2800 2900 3000 3100 3200 3300 3400 3500 3600 

■ 推論所要時間[sec]： 67.6635947227478, 件数：　3641

■ レースの推論結果をCSV（RacePredictedTable.csv）に出力しました

■ SageMakerの「RacePredictedTable.csv」からS3に「RacePredictedTable.csv」としてアップロードしました

-----------------------------------------------------------------------------------------
