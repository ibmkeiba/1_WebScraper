# -*- coding: utf-8 -*-

# ライブラリのインポート
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import chromedriver_binary

from urllib import request as req
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import re
import time
import os


##########################
#  ユーザ関数（スクレイピング）
##########################

""" ①レース開催日の取得 """


# URLからソースコードを取得する関数 <urllib>  【url > soup】
def my_request(url):

    # URLを開く
    res = req.urlopen(url)

    # URLのソースコードを取得
    soup = BeautifulSoup(res, 'html.parser')

    # 暗黙的待機（サーバーの負荷軽減目的）
    time.sleep(0.1)
    
    return soup

# 開催一覧のソースコードから選択中の年月を抽出する関数 【soup > 表示している開催一覧ページの年月（文字列型）】

def my_selected_ym(soup):

    # 選択中の年 > 例 2021
    selected_y = soup.select_one('select#cal_select_year option[selected]').text

    # 選択中の月 > 例 8
    selected_m = soup.select_one('div.RaceNumWrap.CalendarMonth ul li.Active a').text.replace('月', '')

    # 選択中の年月の6桁文字表記 例 202109
    selected_ym = selected_y + selected_m.zfill(2)

    return selected_ym

# 開催一覧のURLから現在の年月と開催がある日を取得 【url > ym（文字列型）, days（整数のリスト型）】
def my_get_raceday_from_url(url_calendar='https://race.netkeiba.com/top/calendar.html', ymd_list=None):

    # URLのソースコードを取得
    soup = my_request(url_calendar)

    # 表示中の年月を取得
    ym = my_selected_ym(soup)

    #レース開催がある日のエレメント（なければ []）
    race_day_elements = soup.select('table.Calendar_Table td.RaceCellBox a')

    # 開催レースが月に一度もなければこれまでの開催日リストを返す
    if race_day_elements == []:
        return ymd_list

    # ymd_listがなければ初期設定
    ymd_list = [] if ymd_list is None else ymd_list
    
    # レース開催がある日を回す
    for ele in race_day_elements:
        
        # レース開催日 例 5
        day = int(ele.select_one('span.Day').text)

        # リストに追加
        ymd_list.append(ym + str(day).zfill(2))

    # 翌月の６桁文字表記（文字列型）
    ym_next = str(int(ym[:4]) + int(ym[4:])//12) + str(int(ym[4:])%12+1).zfill(2)

    # 翌月の開催一覧カレンダーURL
    url_calendar_next = 'https://race.netkeiba.com/top/calendar.html?year=' + ym_next[:4] + '&month=' + str(int(ym_next[4:]))

    return my_get_raceday_from_url(url_calendar_next, ymd_list)


######################################################################


""" ②開催レース一覧 """

# ドライバーを起動 【 - > driver 】
def my_start_driver():

    # オプション設定（★　Colabでそのまま使用できる設定 ★）
    options = webdriver.ChromeOptions()
    options.add_argument('--headless') # Colabではヘッドレス必須*
    options.add_argument('--no-sandbox') # Colab環境でのヘッドレスで必須*
    options.add_argument('--disable-gpu') # soup.prettify() の実行に必要
    options.add_argument('--disable-dev-shm-usage') # メモリ不足回避に有効

    # ドライバーを起動
    driver = webdriver.Chrome('chromedriver', options=options)

    # 要素が見つかるまでの待機時間(秒)を設定
    driver.implicitly_wait(5)

    return driver

# 指定URLのソースコードを取得 【 url > soup 】
def my_get_source_driver(url):

    global driver

    # もしグローバル変数にdriverがなければ起動
    try:
        driver.current_url
    except:
        driver = my_start_driver()
        print('■ driverを起動しました\n')

    # ブラウザでURLにアクセス
    driver.get(url)

    # ソースコードをBeautifulSopuに変換
    html = driver.page_source.encode('utf-8')
    soup = BeautifulSoup(html, 'html.parser')

    return soup

# 目的のレースのエレメントから情報を取得
def my_race_info(race_element):

    # レースURL 'https://', race_url
    race_url = race_element.select_one('a').attrs['href'].replace('..', 'https://race.netkeiba.com')

    # レースID
    race_id = race_url.split('?race_id=')[1].split('&')[0]

    # レース番 '1R', r
    r = race_element.select_one('a div.Race_Num span').text

    # レースタイトル '3歳未勝利', title
    title = race_element.select_one('a span.ItemTitle').text

    # 開始時刻 '10:10 ', time
    start_time = race_element.select_one('a span.RaceList_Itemtime').text

    # コースタイプと距離 'ダ1200m', distance    
    try:
        distance = race_element.select_one('a span.RaceList_ItemLong').text

    except AttributeError:
        distance = race_element.select('a div.RaceData span')[1].text
    
    except:
        print('◆ Select error, ', 'distance ↓')
        distance = ''

    # 出場馬数 '16頭', number
    number = race_element.select_one('a span.RaceList_Itemnumber').text.replace(' ','')

    # レースグレード, '3', grade
    try:
        grade = int(race_element.select_one('a span.Icon_GradeType').attrs['class'][1].replace('Icon_GradeType', ''))
    except: # 存在しない場合
        grade = ''
    else: # 存在する場合
        #grade = int(grade[1].replace('Icon_GradeType', ''))
        pass

    return [r, race_id, start_time, title, grade, number, distance, race_url]

# 開催レース一覧のソースコードから全レースの情報を取得 【 soup > DataFrame 】
def my_race_list(soup):

    # 1日分のレース情報を格納するリスト
    races_list = []

    # 開催年月日（ymd） 文字列型
    ymd = soup.select_one('ul#date_list_sub li.Active').attrs['date']

    # 開催日（曜日）
    date = soup.select_one('ul#date_list_sub li.Active a').attrs['title']

    # 開催場所のエレメントリスト > 3箇所
    place_elelments = soup.select('div.RaceList_Box > dl.RaceList_DataList')

    # 開催場所を回す
    for i, place_ele in enumerate(place_elelments):

        # 開催場所
        place = place_ele.select_one('p.RaceList_DataTitle').text.split(' ')[1]

        # レース一覧のエレメントリスト
        race_elements = place_ele.select('dd.RaceList_Data ul li')

        # レース会場名とレース数を表示
        print('・{}年{}　> {} 【{}】 {} レース'.format(ymd[:4], date, i+1, place, len(race_elements)))

        # レースを回す
        for j, race_ele in enumerate(race_elements):

            # レースのエレメントから情報を取得
            race_list = my_race_info(race_ele)
            # レース情報を表示
            print(race_list)

            # 1日分のレース情報に追加
            races_list.append([int(ymd), date, place] + race_list)
            
    # 1日分のレース情報をDataFrame形式に変換
    ymd_df = pd.DataFrame(races_list, index=None, columns=['ymd', 'date', 'place', 'r', 'race_id', 'start_time', 'title', 'grade', 'number', 'distance', 'url'])

    return ymd_df


######################################################################


""" ③レース出馬表・結果 """

# 出馬表/結果・払戻からレースの情報を取得 【 soup > list 】
def my_result1(soup):

    # 選択されているサブメニュー（出馬表 / 結果・払戻）
    menu = soup.select_one('ul.RaceMainMenu li a.Active').attrs['title']

    # レース開催日
    date = soup.select_one('dl#RaceList_DateList > dd.Active a').text

    # 開催場所
    try:
        place = soup.select_one('div.RaceKaisaiWrap ul li.Active a').text
    except:
        place = soup.select('div.RaceList_NameBox div.RaceData02 span')[1].text

    # レース番号 *
    race_num = int(soup.select_one('div.RaceList_NameBox span.RaceNum').text.replace('R', ''))

    # レース名
    title = soup.select_one('div.RaceList_NameBox div.RaceName').text.replace('\n', '')

    # 発走時刻
    start_time = soup.select_one('div.RaceList_NameBox div.RaceData01').text.replace('\n', '').split('発走')[0]

    # 発走時刻として距離（条件：m）を抽出していた場合は発走時刻を''に修正
    if 'm' in start_time:
        start_time = ''

    # 距離
    distance = soup.select_one('div.RaceList_NameBox div.RaceData01 span').text

    # レース情報の距離'distance'から数値のみ抽出
    longs = int(re.sub(r'\D', '', distance))

    # レース情報の距離 'distance' からコースタイプ（芝, ダ）を抽出
    course = re.sub('\d', '', distance).replace('m', '')

    # レース種別 (要注意)
    race_type = soup.select('div.RaceList_NameBox div.RaceData02 span')[3].text

    # 出馬数 *
    number = int(soup.select('div.RaceList_NameBox div.RaceData02 span')[7].text.replace('頭',''))

    # 賞金金額[万円]
    prize = soup.select('div.RaceList_NameBox div.RaceData02 span')[8].text.replace('本賞金:', '').replace('万円', '')

    #result1_list = [date, menu, place, race_num, title, start_time, distance, race_type, number, prize]
    result1_list = [date, menu, place, race_num, title, start_time, course, longs, race_type, number, prize]

    # 天候と馬場の状態が記載されている場合
    try:
        # 天候 (結果・払戻 限定)
        weather = soup.select_one('div.RaceList_NameBox div.RaceData01').text.split('天候:')[1].split('\n')[0]

        # 馬場の状態 (結果・払戻 限定)
        course_status = soup.select('div.RaceList_NameBox div.RaceData01 span')[-1].text.split('馬場:')[1]

        result1_list = result1_list + [weather, course_status]

    # 天候と馬場の状態が記載されていない場合
    except:
        result1_list = result1_list + ['', '']

    return result1_list

# 【結果・払戻】の１頭分のエレメントから、情報を取得するユーザ関数
def my_result2a(horse_ele):

    # 【結果・払戻】の辞書
    result_dic = {}

    # 着順 ranking
    try:
        result_dic['ranking'] = int(horse_ele.select_one('td.Result_Num > div.Rank').text)
    except:
        return '取り消し'

    # 枠 waku
    result_dic['waku'] = horse_ele.select('td.Num div')[0].text

    # 馬番 umaban
    result_dic['umaban'] = horse_ele.select('td.Num div')[1].text

    # 馬名 bamei
    result_dic['bamei'] = horse_ele.select_one('td.Horse_Info span.Horse_Name a').text

    # 馬のURL bamei_url
    result_dic['bamei_url'] = horse_ele.select_one('td.Horse_Info span.Horse_Name a').attrs['href']

    # 性齢 sexage
    result_dic['sexage'] = horse_ele.select_one('td.Horse_Info span.Lgt_Txt').text.replace('\n', '')

    # 斤量 handicap
    result_dic['handicap'] = horse_ele.select_one('span.JockeyWeight').text

    try:
        # 騎手 jockey
        result_dic['jockey'] = horse_ele.select_one('td.Jockey a').text.replace(' ', '')

        # 騎手のURL jockey_url
        result_dic['jockey_url'] = horse_ele.select_one('td.Jockey a').attrs['href']

    except:
        # 騎手 jockey
        result_dic['jockey'] = horse_ele.select_one('td.Jockey').text.replace('\n', '').replace(' ', '')

        # 騎手のURL jockey_url
        result_dic['jockey_url'] = ''   

    # タイム racetime
    result_dic['racetime'] = horse_ele.select_one('span.RaceTime').text

    # 着差 difference
    result_dic['difference'] = horse_ele.select('span.RaceTime')[1].text

    # 人気 popular
    result_dic['popular'] = horse_ele.select_one('span.OddsPeople').text

    # 単勝オッズ odds
    result_dic['odds'] = horse_ele.select('td.Odds span')[1].text

    # 後3F　furlong3
    result_dic['furlong3'] = horse_ele.select('td.Time')[2].text.replace('\n', '')

    # コーナー通過順 corner_rank
    result_dic['corner_rank'] = horse_ele.select_one('td.PassageRate').text.replace('\n', '')

    # 厩舎(施設名) stable
    result_dic['stable'] = horse_ele.select_one('td.Trainer span').text

    # 厩舎(調教師) trainer
    result_dic['trainer'] = horse_ele.select_one('td.Trainer a').text

    # 厩舎(調教師)のURL trainer_url
    result_dic['trainer_url'] = horse_ele.select_one('td.Trainer a').attrs['href']

    # 馬体重 weight
    try:
        result_dic['weight'] = int(horse_ele.select_one('td.Weight').text.replace('\n', '').split('(')[0])
    except:
        result_dic['weight'] = ''

    # 馬体重の増減 weight_change
    try:
        result_dic['weight_change'] = horse_ele.select_one('td.Weight').text.replace('\n', '').split('(')[1].split(')')[0]
    except:
        result_dic['weight_change'] = ''

    # 取得した情報の表示
    #print(list(result_dic.values()))

    return list(result_dic.values())

# 【出馬表】の１頭分のエレメントから、情報を取得するユーザ関数
def my_result2b(horse_ele):

    # 【出馬表】の辞書
    result_dic = {}

    # 着順 ranking
    result_dic['ranking'] = ''

    # 枠 waku
    result_dic['waku'] = horse_ele.select('td span')[0].text

    # 馬番 umaban
    result_dic['umaban'] = horse_ele.select('td')[1].text

    # 馬名 bamei
    result_dic['bamei'] = horse_ele.select_one('td span.HorseName a').attrs['title']

    # 馬のURL bamei_url
    result_dic['bamei_url'] = horse_ele.select_one('td span.HorseName a').attrs['href']

    # 性齢 sexage
    result_dic['sexage'] = horse_ele.select_one('td.Barei').text

    # 斤量 handicap
    result_dic['handicap'] = horse_ele.select('td')[5].text

    try:
        # 騎手 jockey
        result_dic['jockey'] = horse_ele.select_one('td.Jockey a').attrs['title']

        # 騎手のURL jockey_url
        result_dic['jockey_url'] = horse_ele.select_one('td.Jockey a').attrs['href']

    except:
        # 騎手 jockey
        result_dic['jockey'] = horse_ele.select_one('td.Jockey').text.replace('\n','').replace(' ','')

        # 騎手のURL jockey_url
        result_dic['jockey_url'] = ''

    # タイム racetime
    result_dic['racetime'] = ''

    # 着差 difference
    result_dic['difference'] = ''
    
    # 人気 popular
    result_dic['popular'] = horse_ele.select('td.Popular span')[1].text

    # 単勝オッズ odds
    result_dic['odds'] = horse_ele.select('td.Popular span')[0].text

    # 後3F　furlong3
    result_dic['furlong3'] = ''

    # コーナー通過順 corner_rank
    result_dic['corner_rank'] = ''

    # 厩舎(施設名) stable
    result_dic['stable'] = horse_ele.select_one('td.Trainer span').text

    # 厩舎(調教師) trainer
    result_dic['trainer'] = horse_ele.select_one('td.Trainer a').attrs['title']

    # 厩舎(調教師)のURL trainer_url
    result_dic['trainer_url'] = horse_ele.select_one('td.Trainer a').attrs['href']

    # 馬体重 weight
    try:
        result_dic['weight'] = int(horse_ele.select_one('td.Weight').text.replace('\n', '').split('(')[0])
    except:
        result_dic['weight'] = ''

    # 馬体重の増減 weight_change
    try:
        result_dic['weight_change'] = horse_ele.select_one('td.Weight').text.replace('\n', '').split('(')[1].split(')')[0]
    except:
        result_dic['weight_change'] = ''

    # 取得した情報の表示
    #print(list(result_dic.values()))

    return list(result_dic.values())

# 出馬表 or 結果・払戻 or 取消別にレースの結果を取得 【 horse_ele > def > list 】
def my_result2(horse_ele, menu):

    # 印に取消等があればその馬の情報の抽出を終了
    if horse_ele.select_one('td.Cancel_Txt'):
        return '取り消し'

    # 選択されているサブメニューが "結果・払戻" の場合
    if menu == '結果・払戻':
        return my_result2a(horse_ele)

    # 選択されているサブメニューが "出馬表" の場合
    elif menu == '出馬表':
        return my_result2b(horse_ele)


######################################################################


##########################
# サブメイン関数
##########################

def getkeiba():

    # スクレイピング開始時間
    time1 = time.time()

    """ ①レース開催日の取得 """

    # 指定年月URLからレース開催がある年月日を取得
    ymd_list = my_get_raceday_from_url()
    print('① ', ymd_list)

    ymd_df = pd.DataFrame(ymd_list, columns=['ymd'])
    ymd_df['ymd'].tolist()


    """ ②開催レース一覧 """

    # 全レース情報を格納する空のDataFrameを作成
    races_df = pd.DataFrame()

    # 日を回す d[1:index, 2:d]
    for ymd in ymd_list:

        # レース開催日のURLを作成
        url_ymd = 'https://race.netkeiba.com/top/race_list.html?kaisai_date=' + ymd
        print('\n\n②', ymd, url_ymd, '\n')

        # 全ての会場とレースの情報を取得

        # URL（開催日）のソースコードを取得（selenium）
        soup = my_get_source_driver(url_ymd)

        # 特定日の全レース情報を取得
        race_df = my_race_list(soup)

        # データフレームに追加
        races_df = races_df.append(race_df).reset_index(drop=True)


    """ ③レース出馬表・結果 """

    # 全レースの情報のリスト
    results1_list = []

    # 全レースの結果・払戻のリスト
    results2_list = []

    # レースを回す df[index, row[数値], row['列名']]
    for index, row in races_df.iterrows():

        print('③ {:<5}\t{:<10}\t{:<3}\t{}\t{:<7}\t{:<10}\t\t> '.format(index, row['date'], row['place'], row['grade'], row['r'], row['title']), end='')

        # レースのソースコード取得
        soup = my_request(row['url'])

        # 選択されているサブメニュー（出馬表 / 結果・払戻）
        menu = soup.select_one('ul.RaceMainMenu li a.Active').attrs['title']

        # URLが "結果・払戻" の場合
        if menu == '結果・払戻':

            # レース結果・払戻のトップエレメント
            horse_elements = soup.select('div.ResultTableWrap tr.HorseList')

        # URLが "出馬表" の場合
        elif menu == '出馬表':

            # レースのソースコード取得
            soup = my_get_source_driver(row['url'])

            # レース出馬表のトップエレメント
            horse_elements = soup.select('div.RaceTableArea tr.HorseList')

        # 1. レースの情報を取得　（1レース） ★
        result1_list = my_result1(soup)
        print(result1_list, row['url'])

        # 1. 全レースの情報のリストに追加
        results1_list.append([row['ymd']] + result1_list + [row['grade'], row['race_id'], row['url']])

        # 2. レースの結果・払戻を取得 （1レース）

        # 全馬のレース結果・払戻を取得
        for i, element in enumerate(horse_elements):

            # レース結果・払戻を取得 （1頭） ★
            result2_list = my_result2(element, menu)

            # 取得したレース結果（1頭分）の表示
            #print('\t#{}\t> {}'.format(i+1, result2_list))

            # 2. 全レースの結果・払戻のリストに追加　（完走馬のみ）
            if type(result2_list) == list:
                results2_list.append(result2_list + [row['race_id']])

        # 2. レースの結果・払戻を取得完了 （1レース）の改行 ★
        #print('')

    # ③-1. 全レースの情報のDataFrame
    columns1 = ['ymd', 'date', 'menu', 'place', 'r', 'title', 'start_time', 'course', 'longs', 'race_type', 'number', 'prize', 'weather', 'course_status', 'grade', 'race_id', 'url']
    results1_df = pd.DataFrame(results1_list, index=None, columns=columns1)

    # ③-2. 全レースの結果・払戻のDataFrame
    columns2 = ['ranking', 'waku', 'umaban', 'bamei', 'bamei_url', 'sexage', 'handicap', 'jockey', 'jockey_url', 'racetime', 'difference', 'popular', 'odds', 'furlong3', 'corner_rank', 'stable', 'trainer', 'trainer_url', 'weight', 'weight_change', 'race_id']
    results2_df = pd.DataFrame(results2_list, index=None, columns=columns2)

    # スクレイピング終了時間 / 所要時間を表示
    time2 = time.time()
    print('\n■ スクレイピング所要時間[sec]： ', time2 - time1)

    return (ymd_df, results1_df, results2_df)


##########################
# ユーザ関数（データ出力）
##########################

#
########### 競馬データをCSV出力 ##########
#

def keiba2csv(ymd_df, info_df, result_df):

    # ディレクトリ "data" がなければ作成
    if not os.path.exists('data'):
        os.mkdir('data')

    # csv出力（ ① レース開催一覧 ）
    ymd_df.to_csv('data/RaceDateTable_latest.csv', index=None, header=True, encoding=' utf_8_sig')

    # csv出力（ ② レース情報 ）
    info_df.to_csv('data/RaceInfoTable_latest.csv', index=None, header=True, encoding=' utf_8_sig')

    # csv出力（ ③ レース結果 ）
    result_df.to_csv('data/RaceResultTable_latest.csv', index=None, header=True, encoding=' utf_8_sig')

    print('\n■ 競馬データ（CSV）を「./data/」に出力しました\n')

# 
########### 競馬データをSQLite出力 ##########
#

def keiba2sqlite(ymd_df, info_df, result_df):

    # ライブラリのインポート
    import sqlite3

    # ディレクトリ "data" がなければ作成
    if not os.path.exists('data'):
        os.mkdir('data')

    # データベース（keiba）を作成（既に存在していれば接続）
    conn = sqlite3.connect('data/keiba.db')

    # SQLiteを操作するためのカーソルを作成
    cur = conn.cursor()


    """ 【 1. レース開催一覧 ymd 】 """

    # テーブル（ymd）が存在していれば削除
    cur.execute('DROP TABLE IF EXISTS ymd')

    # テーブル（ymd）を作成
    cur.execute('CREATE TABLE ymd(ymd INTEGER)')
    conn.commit()


    """ 【 2. レース情報 info 】 """

    # テーブル（info）が存在していれば削除
    cur.execute('DROP TABLE IF EXISTS info')

    # テーブル（info）を作成
    cur.execute(""" CREATE TABLE info(

        ymd INT UNSIGNED,
        date TEXT,
        menu TEXT,
        place TEXT,
        r TINYINT,
        title TEXT,
        start_time TEXT,
        course TEXT,
        longs SMALLINT,
        race_type TEXT,
        number TINYINT,
        prize TEXT,
        weather TEXT,
        course_status TEXT,
        grade TINYINT,
        race_id TEXT,
        url TEXT)
        """)
    conn.commit()


    """ 【 3. レース結果 result 】 """

    # テーブル（result）が存在していれば削除
    cur.execute('DROP TABLE IF EXISTS result')

    # テーブル（result）を作成
    cur.execute(""" CREATE TABLE result(

        ranking TINYINT,
        waku TINYINT,
        umaban TINYINT,
        bamei TEXT,
        bamei_url TEXT,
        sexage TEXT,
        handicap FLOAT(3,1),
        jockey TEXT,
        jockey_url TEXT,
        racetime TEXT,
        difference TEXT,
        popular TINYINT,
        odds FLOAT(4,1),
        furlong3 FLOAT(3,1),
        corner_rank TEXT,
        stable TEXT,
        trainer TEXT,
        trainer_url TEXT,
        weight SMALLINT,
        weight_change FLOAT(3,1),
        race_id TEXT)
    """)
    conn.commit()


    # データの一括登録(1. レース開催一覧)
    cur.executemany('INSERT INTO ymd VALUES (?)', ymd_df.values.tolist())
    conn.commit()

    # データの一括登録(2. レース情報)
    cur.executemany('INSERT INTO info VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', info_df.values.tolist())
    conn.commit()

    # データの一括登録(3. レース結果)
    cur.executemany('INSERT INTO result VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', result_df.values.tolist())
    conn.commit()

    # データベースから切断
    cur.close()
    conn.close()

    print('\n■ 競馬データ（SQLite）を「./data/keiba.db」に出力しました(新)\n')


# 
########### 競馬データをMySQL出力 ##########
#
    
def keiba2mysql(ymd_df, info_df, result_df):

    # ドライバをインポート
    import mysql.connector

    # データベース情報を設定
    User = 'xxxx'
    Password = 'xxxx'
    Host = 'xxxamazonaws.com'
    DataBase = 'keiba'

    # データベースに接続（データベース指定あり）
    #conn = mysql.connector.connect(user=User, password=Password, host=Host, database=DataBase,charset='utf8')

    # データベースに接続（データベース指定なし）
    conn = mysql.connector.connect(user=User, password=Password, host=Host ,charset='utf8')

    # MySQLを操作するためのカーソルを作成
    cur = conn.cursor()

    # データベース名 【keiba】 が存在すれば削除
    cur.execute('DROP DATABASE IF EXISTS keiba')

    # データベース名 【keiba】 を作成
    cur.execute('CREATE DATABASE keiba DEFAULT CHARACTER SET utf8')

    # データベース名 【keiba】 を使用
    cur.execute('USE keiba')


    """ 【 1. レース開催一覧 ymd 】 """

    # テーブル（ymd）が存在していれば削除
    cur.execute('DROP TABLE IF EXISTS ymd')

    # テーブル（ymd）を作成
    cur.execute('CREATE TABLE ymd(ymd INTEGER)')
    conn.commit()


    """ 【 2. レース情報 info 】 """

    # テーブル（info）が存在していれば削除
    cur.execute('DROP TABLE IF EXISTS info')

    # テーブル（info）を作成
    cur.execute(""" CREATE TABLE info(

        ymd INT UNSIGNED,
        date TEXT,
        menu TEXT,
        place TEXT,
        r TINYINT,
        title TEXT,
        start_time TEXT,
        course TEXT,
        longs SMALLINT,
        race_type TEXT,
        number TINYINT,
        prize TEXT,
        weather TEXT,
        course_status TEXT,
        grade TINYINT,
        race_id TEXT,
        url TEXT)
    """)
    conn.commit()


    """ 【 3. レース結果 result 】 """

    # テーブル（result）が存在していれば削除
    cur.execute('DROP TABLE IF EXISTS result')

    # テーブル（result）を作成
    cur.execute(""" CREATE TABLE result(

        ranking TINYINT,
        waku TINYINT,
        umaban TINYINT,
        bamei TEXT,
        bamei_url TEXT,
        sexage TEXT,
        handicap FLOAT(3,1),
        jockey TEXT,
        jockey_url TEXT,
        racetime TEXT,
        difference TEXT,
        popular TINYINT,
        odds FLOAT(4,1),
        furlong3 FLOAT(3,1),
        corner_rank TEXT,
        stable TEXT,
        trainer TEXT,
        trainer_url TEXT,
        weight SMALLINT,
        weight_change FLOAT(3,1),
        race_id TEXT,
        ranking_pre TINYINT,
        racetime_pre TEXT)
    """)
    conn.commit()


    # データの一括登録(1. レース開催一覧)【ymd】> ymd
    cur.executemany('INSERT INTO ymd (ymd) VALUES (%s)', ymd_df.values.tolist())
    conn.commit()

    # MySQL登録用のデータフレームを作成【info】> ymd
    info_sql = info_df.copy()
    info_sql['grade'] = info_df['grade'].replace('',np.nan).replace([np.nan],[None])

    # データの一括登録(2. レース情報)【info】> 全て
    cur.executemany('INSERT INTO info (ymd,date,menu,place,r,title,start_time,course,longs,race_type,number,prize,weather,course_status,grade,race_id,url) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)', info_sql[['ymd','date','menu','place','r','title','start_time','course','longs','race_type','number','prize','weather','course_status','grade','race_id','url']].values.tolist())
    conn.commit()

    # MySQL登録用のデータフレームを作成【result】> ranking, waku, umaban, furlong3, weight, weight_change, 
    result_sql = result_df.copy()
    result_sql['ranking'] = result_df['ranking'].replace('',np.nan).replace([np.nan],[None])
    result_sql['waku'] = result_df['waku'].replace('',np.nan).replace([np.nan],[None])
    result_sql['umaban'] = result_df['umaban'].replace('',np.nan).replace([np.nan],[None])
    result_sql['handicap'] = result_df['handicap'].replace('',np.nan).replace('未定',np.nan).replace([np.nan],[None])
    result_sql['furlong3'] = result_df['furlong3'].replace('',np.nan).replace([np.nan],[None])
    result_sql['weight'] = result_df['weight'].replace('',np.nan).replace([np.nan],[None])
    result_sql['weight_change'] = result_df['weight_change'].replace('',np.nan).replace([np.nan],[None])

    # データの一括登録(3. レース結果)【result】> 全て
    cur.executemany('INSERT INTO result (ranking,waku,umaban,bamei,bamei_url,sexage,handicap,jockey,jockey_url,racetime,difference,popular,odds,furlong3,corner_rank,stable,trainer,trainer_url,weight,weight_change,race_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)', result_sql[['ranking','waku','umaban','bamei','bamei_url','sexage','handicap','jockey','jockey_url','racetime','difference','popular','odds','furlong3','corner_rank','stable','trainer','trainer_url','weight','weight_change','race_id']].values.tolist())
    conn.commit()

    # データベースから切断
    cur.close()
    conn.close()

    print('\n■ 競馬データ（MySQL）を「keiba」に出力しました\n')

    
##########################
# メイン関数
##########################

def main():

    # レース開催一覧, レース情報, レース結果 をスクレイピングして取得 【 None > DataFrame *3】
    ymd_df, info_df, result_df = getkeiba()

    # 競馬データをCSV出力
    keiba2csv(ymd_df, info_df, result_df)

    # 競馬データをSQLite出力
    keiba2sqlite(ymd_df, info_df, result_df)

    # 競馬データをMySQL出力
    keiba2mysql(ymd_df, info_df, result_df)

if __name__ == '__main__':
    main()
