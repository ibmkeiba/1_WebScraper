# -*- coding: utf-8 -*-

# ライブラリのインポート
import mysql.connector
import pandas as pd
import numpy as np
import re
import os

# 実行環境の設定 'local' / 'aws'
HOST = 'aws'

##########################
#  ユーザ関数
##########################


""" データベースに接続（ローカル / AWS） """

def connect_db(db = '', host = HOST):
    
    # データベース接続（AWS:MySQL）
    if host == 'aws':
        
        User = 'root'
        Password = 'ibmer2021'
        Host = 'temaa-test-db.cyyyxfovd2dz.ap-northeast-1.rds.amazonaws.com'
        
        return mysql.connector.connect(user=User, password=Password, host=Host, database=db,charset='utf8')
        
    # データベース接続（ローカル:MySQL）
    else:
        return mysql.connector.connect(user='root', password='root', host='localhost', database=db)


######################################################################


""" MySQLの'keiba'データベースから機械学習推論用データを作成 """

def makelearn():
    
    # 1. レース情報の取得

    # データベースに接続
    conn = connect_db(db = 'keiba', host = HOST)
    
    # MySQLを操作するためのカーソルを作成
    cur = conn.cursor()

    # カラム名の取得 info
    cur.execute('DESC info')
    columns_info = pd.DataFrame(cur.fetchall()).iloc[:][0].tolist()

    # SQLからレース情報を読み出し
    cur.execute('SELECT * FROM info')
    info_df = pd.DataFrame(cur.fetchall(), columns = columns_info)

    
    # 2. レース結果の取得

    # カラム名の取得 info
    cur.execute('DESC result')
    columns_result = pd.DataFrame(cur.fetchall()).iloc[:][0].tolist()

    # SQLからレース結果を読み出し
    cur.execute('SELECT * FROM result')
    result_df = pd.DataFrame(cur.fetchall(), columns = columns_result)

    # データベースから切断
    cur.close()
    conn.close()
    

    # 3. レーズ情報のレース結果に追加するDataFrameを作成

    # 追加するレース情報をリストで設定
    info_selects = ['number', 'course', 'longs', 'weather', 'course_status', 'date', 'url', 'race_id']

    # 指定した行条件を満たす, 指定した列を抽出（レース結果のIDを回して, レース情報の複数列を取得）
    info_add_list = [info_df[info_df['race_id'] == str(id)].loc[:, info_selects].iloc[0].tolist() for id in result_df['race_id']]

    # レース情報を追加したレース結果のDataFrameを作成（race_idをint型に変換）
    info_add_df = pd.DataFrame(info_add_list, index=None, columns=info_selects)

    # 列名を変更
    info_add_df.rename(columns={'longs': 'distance', 'num': 'number'})


    # 4. レース結果の一部の新しいデータ形式のDataFrameを作成

    # レース結果の記録タイム 'racetime' を秒単位の数値型に変換 ※nanがある場合の対応を追加
    sec = [int(time.split(':')[0])*60.0 + float(time.split(':')[1]) if time != '' else np.nan for time in result_df['racetime']]

    # レース結果の性齢 'sexage' から性（牡, 牝, セ）を抽出
    sex = [re.sub(r'\d', '', sexage) for sexage in result_df['sexage']]

    # レース結果の性齢 'sexage' から歳を抽出
    age = [re.sub(r'\D', '', sexage) for sexage in result_df['sexage']]

    # レース結果のDataFrameに変換後の列を追加（RaceResultTable）
    result_add_df = pd.DataFrame([sec, sex, age], index = ['sec', 'sex', 'age']).T


    # 5. レース情報とレース結果の新しいデータ形式のDataFrameを作成
    add_df = pd.concat([result_add_df.reset_index().drop('index', axis=1), info_add_df.reset_index().drop(['index', 'race_id'], axis=1)], axis=1)


    # 6. 推論に利用する項目のDataFrameを作成

    # 推論用レース情報・結果データの項目をセレクト（推論時の並び順）
    select_list = ['waku', 'umaban', 'bamei', 'handicap', 'popular', 'odds', 'furlong3', 'weight', 'weight_change', 'sec', 'sex', 'age', 'number', 'course', 'longs', 'weather', 'course_status', 'race_id']

    # 推論するレース情報・結果データのDataFrameを作成（ waku が存在するレコードのみ ）
    select_df = pd.concat([result_df.reset_index().drop('index', axis=1), add_df.reset_index().drop('index', axis=1)], axis=1)[select_list].dropna(subset=['waku'])


    # 7. 推論入力形式の文字列を追加したDataFrameを作成（SQLに保存するテーブルlearn形式）

    # 推論に渡す文字列リストを作成
    ls = [ ','.join(row.replace(np.nan, '').drop(['race_id', 'sec']).astype(str).tolist()) for index, row in select_df.iterrows() ]

    # 機械学習入力データのテーブル"learn"とするDataFraemを作成
    learn_df = select_df.copy()
    learn_df['test'] = ls
    
    print('\n■ 競馬データの機械学習推論データを作成しました\n')

    return learn_df


######################################################################


""" 機械学習推論用データをCSV出力 """

def learn2csv(learn_df):
    
    # ディレクトリ "data" がなければ作成
    if not os.path.exists('data'):
        os.mkdir('data')

    # csv出力（ 推論用データ ）
    learn_df.to_csv('data/RaceLearnTable_latest.csv', index=None, header=True, encoding=' utf_8_sig')

    print('\n■ 競馬データの機械学習推論データ（CSV）を「./data/」に出力しました\n')


######################################################################


""" 機械学習推論用データをSQL登録 """

def learn2sql(learn_df):
    
    # データベース接続
    conn = connect_db('keiba')
    cur = conn.cursor()

    # テーブル（learn）が存在していれば削除
    cur.execute('DROP TABLE IF EXISTS learn')

    # テーブル（learn）を作成
    cur.execute(""" CREATE TABLE learn(
    
        waku TINYINT,
        umaban TINYINT,
        bamei TEXT,
        handicap FLOAT(3,1),
        popular TINYINT,
        odds FLOAT(4,1),
        furlong3 FLOAT(3,1),
        weight SMALLINT,
        weight_change FLOAT(3,1),

        sec FLOAT(4,1),
        sex TEXT,
        age TINYINT,

        number TINYINT,
        course TEXT,
        longs SMALLINT,
        weather TEXT,
        course_status TEXT,
        race_id TEXT,
        test TEXT)

    """)
    conn.commit()
    

    # MySQL登録用のデータフレームに整形【result】> ranking, waku, umaban, furlong3, weight, weight_change, 
    learn_sql = learn_df.copy()
    learn_sql['waku'] = learn_df['waku'].replace('',np.nan).replace([np.nan],[None])
    learn_sql['umaban'] = learn_df['umaban'].replace('',np.nan).replace([np.nan],[None])
    learn_sql['handicap'] = learn_df['handicap'].replace('',np.nan).replace('未定',np.nan).replace([np.nan],[None])
    learn_sql['furlong3'] = learn_df['furlong3'].replace('',np.nan).replace([np.nan],[None])
    learn_sql['weight'] = learn_df['weight'].replace('',np.nan).replace([np.nan],[None])
    learn_sql['weight_change'] = learn_df['weight_change'].replace('',np.nan).replace([np.nan],[None])

    # データの一括登録(3. レース結果)【result】> 全て
    cur.executemany('INSERT INTO learn (waku,umaban,bamei,handicap,popular,odds,furlong3,weight,weight_change,sec,sex,age,number,course,longs,weather,course_status,race_id,test) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)', learn_sql[['waku','umaban','bamei','handicap','popular','odds','furlong3','weight','weight_change','sec','sex','age','number','course','longs','weather','course_status','race_id','test']].values.tolist())
    conn.commit()

    # データベースから切断
    cur.close()
    conn.close()

    print('\n■ 競馬データの機械学習推論データ（MySQL）を「keiba > learn」に出力しました\n')


######################################################################


""" 機械学習推論用データをAWSのS3にアップロード """

def uploads3(localfile, s3file):

    import boto3

    # S3バケット名の指定
    bucket = 'teama-s3-sagemaker'

    # localからS3にアップロード
    s3 = boto3.resource('s3')
    s3.Bucket(bucket).upload_file(localfile, s3file)

    print(f'\n■ EC2の「{localfile}」からS3に「{s3file}」としてアップロードしました\n')


######################################################################


""" 機械学習推論用結果をAWSのS3からダウンロード """

def downloads3(s3file, localfile):

    import boto3

    # S3バケット名の指定
    bucket = 'teama-s3-sagemaker'

    # S3からlocalにダウンロード
    s3 = boto3.resource('s3')
    s3.Bucket(bucket).download_file(s3file, localfile)

    print(f'\n■ S3の「{s3file}」からEC2に「{localfile}」としてダウンロードしました\n')



######################################################################


""" 推論結果のCSVファイルからSQLのresultを更新 """

def predict2sql():
    
    # 推定結果のCSVファイルをDataFrameとして読み込み
    pre_df = pd.read_csv('data/RacePredictedTable.csv')
    
    # データベースに接続
    conn = connect_db('keiba')
    cur = conn.cursor()
    
    # 推定結果のレコードを回す
    for index, row in pre_df.iterrows():

        # データの更新に必要な項目の整形
        race_id = str(row['race_id'])
        umaban = int(row['umaban'])
        ranking_pre = int(row['ranking_pre'])
        racetime_pre = '{}:{:.1f}'.format(round(row['racetime_pre']//60), row['racetime_pre']%60)
        #racetime_pre = str(round(row['racetime_pre'], 1))

        param = [ranking_pre, racetime_pre, race_id, umaban]

        # データの更新
        cur.execute('UPDATE result SET ranking_pre = %s, racetime_pre = %s WHERE race_id = %s AND umaban = %s', param)
        conn.commit()
    
    print('\n■ データベースのレース結果（result）の予測着順・予測タイムを更新しました\n')


######################################################################

##########################
# メイン関数
##########################

def main():

    # MySQLの'keiba'データベースから機械学習推論用データを作成
    learn_df = makelearn()

    # 機械学習推論用データをSQL登録
    learn2sql(learn_df)

    # 機械学習推論用データをCSV出力
    learn2csv(learn_df)

    # 機械学習推論用データをAWSのS3にアップロード
    uploads3('data/RaceLearnTable_latest.csv', 'RaceLearnTable_latest.csv')

    # 機械学習推論用結果をAWSのS3からダウンロード
    downloads3('RacePredictedTable.csv', 'data/RacePredictedTable.csv')

    # 推論結果のCSVファイルからSQLのresultを更新
    predict2sql()


if __name__ == '__main__':
    main()