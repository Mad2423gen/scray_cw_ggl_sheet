import requests
import lxml
from bs4 import BeautifulSoup
import os
import time
from retrying import retry


# todo: 実装後気がついたこと、【改善アイディア】　
#  １．表示画面がそっけない、もうちょっとかっこよく　
#  ２．ステータス画面の行がずれてる

# 初期設定の指定：返り値はリスト化されたファイル名
def conf_read():
	# 【初期設定】----------------------------------------------------------------
	path = os.getcwd()
	# 過去の案件ファイル
	job_file = os.path.join(path, 'joblist_cw.txt')
	# ターゲットURLファイル
	target_url_file = os.path.join(path, 'clowdworks_url')
	# --------------------------------------------------------------------------
	conf_vals = {'job_file': job_file, 'target_url_file': target_url_file}
	return conf_vals


# webページソース取得
def websourceget(target_url):
	# ページソース取得
	souece = requests.get(target_url)
	return souece


# タグからデータを取得、返り値はデータリスト
@retry(wait_fixed=1000)  # 接続エラー時にリトライ、間隔は１秒毎
def get_datalist_cloudworks(page_source):
	soup = BeautifulSoup(page_source.text, 'lxml')
	# 各タグからデータ取得---------------------------------------------
	# タイトルテキストとURL
	tag_titles = 'div.job_data_column.summary > h3 > a'
	titles = soup.select(tag_titles)
	# 募集人数
	applicants = soup.select('span.contract_hope_number_cell')
	# リスト格納
	NewApplicationList = []
	# 補完用URL
	addition_url = 'https://crowdworks.jp/'
	for title, applicant in zip(titles, applicants):
		NewApplicationList.append([title.text,
								   applicant.text.replace('\n', '').replace(' ', ''),
								   addition_url + title.attrs['href']])
	# 新規リスト取得終------------------------------------------------
	return NewApplicationList


# データの差分の検出=NewApplicationList, OldApplicationListはリスト
def differential_extraction(NewApplicationList, OldApplicationList):
	"""
	【処理の流れ】
	新しいデータの件名が旧データに含まれているか確認
		有　→　pass
		無　→　SendMessageList に追加
	増分を SendMessageList で返す
	"""

	# 差分比較--------------------------------------------------------
	# 旧リストに含ま入れない案件を抽出
	SendMessageList = []
	for NewItem in NewApplicationList:
		if NewItem[0] in OldApplicationList:
			pass
		else:
			# print(NewItem[0], NewItem[1], NewItem[2])
			SendMessageList.append([NewItem[0], NewItem[1], NewItem[2]])
	return SendMessageList  # 返り値は増分のリスト


# Pushbullet メッセージ送信
# Pushbulletの送信
def send_bullet(msg_list):
	"""
	---------------------------------------------------------------
	通知をPushbulletに送信
	モジュールの使い方は以下URL参照
	https://laboratory.kazuuu.net/install-and-use-the-pushbullet-library-in-python/
	---------------------------------------------------------------
	"""
	from pushbullet import Pushbullet
	if msg_list:
		print('Send messages via Pushbullet')
		# トークンインポート
		with open('pushbullet_token', 'r', encoding='utf-8_sig') as f:
			pushbullet_token = f.readline()
		pd = Pushbullet(pushbullet_token)

		# 送信
		for MessgeList in msg_list:
			# 第一引数はタイトル、第二引数は本文
			print(f'busy: {MessgeList[0]}')
			push = pd.push_note('Scrayping-tool',
								f"{MessgeList[0]}  {MessgeList[1]} \n{MessgeList[2]}")
		print('		Msg send Completed')


# 過去データとの比較用なので、件名のみ保存する
def data_save(save_data, filename, mode):
	if mode == 1:
		# 追記
		print('		Data saving...')
		with open(filename, 'a', encoding='utf-8_sig') as sf:
			for lst in save_data:
				sf.write(lst[0])  # 案件の件名のみ保存する
				sf.write(os.linesep)  # 改行コード挿入（テキストファイルの可読性維持のため）
	elif mode == 2:
		# 上書き
		print('		Data saving...')
		with open(filename, 'w', encoding='utf-8_sig') as sf:
			for lst in save_data:
				sf.write(lst[0])  # 案件の件名のみ保存する
				sf.write(os.linesep)  # 改行コード挿入（テキストファイルの可読性維持のため）


# job_fileの初期化処理（差分検出、送信なし）データは'joblist_cw.txt'に保存
def ini_func():
	setting = conf_read()
	joblist = []
	with open(setting['target_url_file'], 'r', encoding='utf-8_sig') as tf:
		urls = tf.readlines()
		for url in urls:
			res = websourceget(url)
			item_lists = get_datalist_cloudworks(res)
			data_save(item_lists, setting['job_file'], 1)


# 通常処理（ソース取得、タグ検出）帰り値は新規案件の全データ
def func_nomal():
	setting = conf_read()
	with open(setting['target_url_file'], 'r', encoding='utf-8_sig') as nf:
		urls = nf.readlines()
		all_lists = []
		for url in urls:
			res = websourceget(url)
			new_list = get_datalist_cloudworks(res)
			for ls in new_list:
				all_lists.append(ls)
	old_subject = []  # 件名のみ保存する配列
	# 古ファイル読込
	with open(setting['job_file'], 'r', encoding='utf-8_sig') as of:
		old_lists = of.readlines()  # 注意：呼び出されるのは件名だけ
		for old_list in old_lists:
			# 件名のみ格納
			old_subject.append(old_list.replace('\n', ''))  # 改行を削除、配列へ格納

	# 差分抽出、差分リスト作成(送信と追記に使用）
	for sbj in old_subject:
		difflists = differential_extraction(all_lists, old_subject)

	# 送信処理
	send_bullet(difflists)
	# 古ファイルを更新
	data_save(all_lists, setting['job_file'], 2)


# メニュー・例外時の処理実行
def func_menu():
	# 【初期設定】----------------------------------------------------------------
	path = os.getcwd()
	# 過去の案件ファイル
	job_file = os.path.join(path, 'joblist_cw.txt')
	# ターゲットURLファイル
	target_url_file = os.path.join(path, 'clowdworks_url')
	# --------------------------------------------------------------------------

	# 【処理開始】

	# 例外処理：job_fileがない場合、更新処理を自動実行
	if os.path.isfile(job_file):
		pass
	else:
		print("*** No past files, initialize ***")
		ini_func()
	# 例外処理終

	# メニュー：「1.通常実行　2.過去ファイルを初期化して実行」
	print("""
	******************************************************
	CloudWorks Scrayping
		Please select an execution mode
		1. Processing start
		2. Initialization of saved data
	******************************************************
	""")
	sel_num = input('	Press input num :')  # 入力
	return sel_num


if __name__ == '__main__':
	select_num = func_menu()
	# 1 = 通常処理
	# 2 = 初期化処理
	if int(select_num) == 1:
		tt = input("time interval：")
		while True:
			func_nomal()
			print('Standby')
			time.sleep(int(tt))
	elif int(select_num) == 2:
		tt = input("time interval：")
		# 初期化処理　→　通常処理のループ
		ini_func()
		while True:
			func_nomal()
			print('Standby')
			time.sleep(int(tt))
	else:
		print('Please enter the correct mode number')
