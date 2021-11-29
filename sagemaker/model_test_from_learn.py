# ライブラリのインポート
import boto3
import pandas as pd
import time
import sys


# S3バケットから機械学習推論用データをダウンロードして読み込み： None > DataFrame (ls_df)

def MyGetLearnFromS3(filepath='RaceLearnTable_latest.csv'):

    # S3バケット名の指定
    bucket = 'teama-s3-sagemaker'

    # ダウンロード
    s3 = boto3.resource('s3')
    s3.Bucket(bucket).Object(filepath).download_file('RaceLearnTable.csv')
    
    print(f'\n■ SageMakerの「{filepath}」からS3に「RaceLearnTable.csv」としてダウンロードしました\n')

    # DataFrameとして読み込み
    ls_df = pd.read_csv('RaceLearnTable.csv')

    return ls_df


# 推論を実行：　DataFrame (ls_df) > DataFrame (resultall_df)

def MyPredict(ls_df, ep_name):
    
    # エンドポイントのセッション開始 (Heavy)
    sm_rt = boto3.Session().client('runtime.sagemaker')

    # 予想タイムのリスト実行数カウンターの初期設定
    sec_list = []
    count = 0

    # 推論の開始時間
    time1 = time.time()

    for index, row in ls_df.iterrows():

        # 推論用の文字列を作成
        l = row['test']

        # エンドポイントにデプロイ
        responses = sm_rt.invoke_endpoint(EndpointName=ep_name, ContentType='text/csv', Accept='text/csv', Body=l)

        # 返答結果の予測値
        res = responses['Body'].read().decode("utf-8")

        # 着順予想タイムのリストに追加
        sec_list.append(float(res))

        # 進行状況を表示（100単位）
        count += 1
        if (count % 100 == 0):   
            sys.stdout.write(str(count)+' ')

    # 推論の終了時間 / 所要時間を表示
    time2 = time.time()
    print(f'\n\n■ 推論所要時間[sec]： {time2 - time1}, 件数：　{count}')

    # レースID, 予想着順, 予想順位 のDataFrameを作成
    pre_df = pd.DataFrame([ls_df['race_id'].astype(int).tolist(), sec_list], index=['race_id','racetime_pre']).T
    pre_df['ranking_pre'] = pre_df.groupby(['race_id']).rank(method='min').astype(int)

    # レース結果に予想着順と予想タイムを合わせたDataFrameを作成
    resultall_df = pd.concat([ls_df.reset_index().drop('index', axis=1), pre_df.reset_index().drop(['index', 'race_id'], axis=1)], axis=1)

    return resultall_df


# レース結果のレコードを特定できる情報と推論結果のDataFrameを作成してCSV出力
def learn2csv(resultall_df, filepath='RacePredictedTable.csv'):
    
    # 推論結果とレコードを特定できる項目のDataFrame
    selected = ['race_id', 'umaban', 'bamei', 'ranking_pre', 'racetime_pre']
    learn_df = resultall_df[selected]

    # CSV出力
    learn_df.to_csv(filepath, index=None, header=True, encoding=' utf_8_sig')
    
    print(f'\n■ レースの推論結果をCSV（{filepath}）に出力しました\n')


# 機械学習推論用データをS3にアップロード
def uploads3(filepath='RacePredictedTable.csv'):

    # S3バケット名の指定
    bucket = 'teama-s3-sagemaker'

    s3 = boto3.resource('s3')
    s3.Bucket(bucket).Object(filepath).upload_file(filepath)

    print(f'■ SageMakerの「{filepath}」からS3に「{filepath}」としてアップロードしました\n')


def main():
    
    # S3バケットから機械学習推論用データをダウンロードして読み込み： None > DataFrame (ls_df)
    ls_df = MyGetLearnFromS3()

    # 推論を実行：　DataFrame (ls_df, エンドポイント名) > DataFrame (resultall_df)　
    resultall_df = MyPredict(ls_df, 'Keiba-Heavy-2008-2021-1129')

    # レース結果のレコードを特定できる情報と推論結果のDataFrameを作成してCSV出力
    learn2csv(resultall_df)

    # 機械学習推論用データをS3にアップロード
    uploads3()


# 一連の実行
main()
