import os
import pandas as pd
from googleapiclient.discovery import build
import re
import networkx as nx
import matplotlib.pyplot as plt
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

ytapikey = 'AIzaSyAmNNGOxx4DvCGJj_V8qHP5N4PD9J5Btns'
bnyknyakomen = 1000

def get_comments(yt, videoid, page_token=None):
    response = yt.commentThreads().list(
        part='snippet',
        videoId=videoid,
        maxResults=bnyknyakomen,
        pageToken=page_token
    ).execute()
    return response

def crawl_comments(videoid):
    yt = build('youtube', 'v3', developerKey=ytapikey)
    comments = []

    page_token = None
    while True:
        response = get_comments(yt, videoid, page_token)
        for item in response['items']:
            comment = item['snippet']['topLevelComment']['snippet']
            username = comment['authorDisplayName']
            comment_text = comment['textDisplay']
            comment_date = comment['updatedAt']
            comments.append((username, comment_text, comment_date))

        if 'nextPageToken' not in response:
            break

        page_token = response['nextPageToken']

    return comments

def save_comments_to_csv(comments, output_file=''):
    df = pd.DataFrame(comments, columns=['Username', 'Comment', 'Comment Date'])
    df.to_csv(output_file, index=False)
    print(f"Komentar berhasil disimpan dalam file {output_file}")

currentFile = ''

def create_charts(kw_results):
    plt.figure(figsize=(6, 6))
    plt.pie(kw_results.values(), labels=kw_results.keys(), autopct='%1.1f%%', startangle=140)
    plt.axis('equal')
    plt.title('Persentase Kemunculan Kata Kunci')
    plt.savefig('static/pie_chart.png')
    plt.close()

    plt.figure(figsize=(10, 5))
    plt.bar(kw_results.keys(), kw_results.values(), color='skyblue')
    plt.xlabel('Kata Kunci')
    plt.ylabel('Kemunculan')
    plt.title('Jumlah Kemunculan Kata Kunci')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('static/bar_chart.png')
    plt.close()

@app.route('/', methods=['GET', 'POST'])
def index():
    global currentFile
    if request.method == 'POST':
        videoid = request.form['videoid']
        file_name = request.form['file_name']
        currentFile = file_name+'.csv'
        comments = crawl_comments(videoid)
        save_comments_to_csv(comments, currentFile)
        return redirect(url_for('graph'))

    return render_template('index.html')

@app.route('/graph', methods=['GET', 'POST'])
def graph():
    global currentFile
    if request.method == 'POST':
        videoid = request.form['videoid']
        file_name = request.form['file_name']
        currentFile = file_name+'.csv'
        comments = crawl_comments(videoid)
        save_comments_to_csv(comments, currentFile)
        return redirect(url_for('graph'))
    
    df = pd.read_csv(currentFile)
    df['Comment'] = df['Comment'].apply(lambda x: re.sub(r'[^a-zA-Z\s]', '', x))

    kw = request.args.get('keywords', '').split(',')
    max_kw = int(request.args.get('max_keywords', 3))

    kw = kw[:max_kw]

    G = nx.Graph()

    G.add_node('presiden')

    keyword_colors = {}

    for i, kwd in enumerate(kw):
        keyword_node = kwd.strip()
        G.add_node(keyword_node)

        colors = ['skyblue', 'orange', 'green', 'purple', 'yellow', 'pink', 'gray', 'brown', 'cyan']
        keyword_colors[keyword_node] = colors[i % len(colors)]

        G.add_edge('presiden', keyword_node)

    kwd_data = {}

    for index, row in df.iterrows():
        Username = row['Username']
        Comment = row['Comment']

        for kwd in kw:
            if kwd.strip().lower() in Comment.lower():
                G.add_edge(kwd.strip(), Username)

    filtered_df = df[df['Comment'].str.contains('|'.join(kw), case=False)]
    filtered_df.to_csv('data_filtered_youtube.csv', index=False)

    pos = nx.fruchterman_reingold_layout(G, seed=40)
    plt.figure(figsize=(10, 7))
    node_colors = [keyword_colors[node] if node in keyword_colors else 'red' for node in G.nodes()]
    nx.draw(G, pos, with_labels=False, node_color=node_colors, font_size=11, font_weight='bold', node_size=20)
    plt.title('Social Network Analysis (SNA) Graph')
    plt.savefig('static/graph.png')
    plt.close()

    kw_results = {}

    for kwd in kw:
        kw_data = filtered_df['Comment'].str.count(kwd.strip(), re.IGNORECASE).sum()
        kw_results[kwd.strip()] = kw_data

    create_charts(kw_results)

    return render_template('graph.html', keyword_colors=keyword_colors)

if __name__ == '__main__':
    app.run(debug=True)