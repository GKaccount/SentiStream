# import pandas as pd
import os.path
import urllib.parse
from flask import Flask, request, render_template, redirect, session, url_for
import requests
# import pandas as pd
from scrape import *
import matplotlib.pyplot as plt
import base64
from io import BytesIO
import re
import flask
import requests
from textblob import TextBlob
import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery



app = Flask(__name__, template_folder='template')
app.secret_key = 'your_secret_key'


@app.route('/')
def home():
    return render_template('home.html')

@app.route('/about')
def aboutus():
    return render_template('about.html')

@app.route('/result', methods=['GET', 'POST'])
def result():
    id = request.form.get('url')
    video_id = get_video_id(id)
    fileName = request.form.get("file_name")

    api_url = f'https://www.googleapis.com/youtube/v3/videos'
    params = {
        'id': video_id,
        'part': 'snippet',
        'key': api_key,
    }

    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()  # Raise HTTPError for bad responses

        data = response.json()

        if 'items' in data and data['items']:
            flag = 1
        else:
            flag = 0
    except requests.exceptions.HTTPError:
        flag = 2
    except Exception:
        flag = 3

    if flag == 1:
        df = video_comments(video_id)
        lst = get_video_stats(video_id)

        try:
            if isinstance(df, pd.DataFrame):
                res, file_path = sentiment_analyzer(df, fileName)
                dataFrame = pd.read_csv(file_path)
                dataFrame1 = dataFrame[dataFrame['Label'] == "Positive"]
                dataFrame2 = dataFrame[dataFrame['Label'] == "Neutral"]
                dataFrame3 = dataFrame[dataFrame['Label'] == "Negative"]
                l1 = len(res[res['Label'] == 'Positive'])
                l2 = len(res[res['Label'] == 'Neutral'])
                l3 = len(res[res['Label'] == 'Negative'])
                values = [l1, l2, l3]
                labels = ['Positive', 'Neutral', 'Negative']
                colors = ['Limegreen', 'silver', 'red']

                explode = (0, 0, 0.1)
                fig, ax = plt.subplots(figsize=(4.3, 4.3))

                ax.pie(values, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90, explode=explode)
                ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle

                plt.title('Sentiment Distribution')

                # Save the chart as an image
                img_buffer = BytesIO()
                plt.savefig(img_buffer, format='png')
                img_buffer.seek(0)
                img_str = base64.b64encode(img_buffer.read()).decode('utf-8')
                plt.close()

                plt.figure(figsize=(5, 4))
                plt.bar(labels, values, color=colors)
                plt.title('Sentiment Distribution in YouTube Comments')
                plt.xlabel('Sentiment')
                plt.ylabel('Number of Comments')
                bar_buffer = BytesIO()
                plt.savefig(bar_buffer, format='png')
                bar_buffer.seek(0)
                bar_str = base64.b64encode(bar_buffer.read()).decode('utf-8')
                plt.close()

                wordcloud = generate_cloud(dataFrame.Comment)
                fig1, ax1 = plt.subplots(figsize=(8, 8))
                ax1.imshow(wordcloud, interpolation='bilinear')
                ax1.axis('off')
                save_folder = 'static'
                file_extension = 'png'
                saveFileName = f"{save_folder}/{fileName}.{file_extension}"
                plt.savefig(saveFileName, bbox_inches='tight', pad_inches=0.1)

                return render_template('result.html',
                                       pie_chart=img_str,
                                       frequent_words=saveFileName,
                                       emojis=bar_str,
                                       data=dataFrame,
                                       scraped=dataFrame.shape[0],
                                       df1=dataFrame1.to_dict(
                                           orient='records'),
                                       df2=dataFrame2.to_dict(
                                           orient='records'),
                                       df3=dataFrame3.to_dict(
                                           orient='records'),
                                       value=True,
                                       Title=lst[0],
                                       ChannelName=lst[1],
                                       Views=lst[2],
                                       Likes=lst[3],
                                       TotalComments=lst[4],
                                       PublishedAt=lst[5],
                                       urls=video_id,
                                       flag=1,
                                       downloads=file_path,
                                       fileName=fileName
                                       )
        except ValueError:
            return render_template('result.html', titles=[''],
                                   value=False,
                                   Title=lst[0],
                                   ChannelName=lst[1],
                                   Views=lst[2],
                                   Likes=lst[3],
                                   TotalComments=lst[4],
                                   PublishedAt=lst[5],
                                   urls=video_id,
                                   flag=1
                                   )
        else:
            return render_template('result.html', titles=[''],
                                   value=False,
                                   Title=lst[0],
                                   ChannelName=lst[1],
                                   Views=lst[2],
                                   Likes=lst[3],
                                   TotalComments=lst[4],
                                   PublishedAt=lst[5],
                                   urls=video_id,
                                   flag=1
                                   )

    elif flag == 0:
        return render_template("result.html", flag=0)
    elif flag == 2:
        return render_template("result.html", flag=2)
    else:
        return render_template("result.html", flag=3)


def get_video_id(video_id):
    # Regular video ID pattern
    regular_pattern = re.compile(
        r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?['
        r'?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})')

    # Shorts video ID pattern
    shorts_pattern = re.compile(
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})')

    # Check for regular video ID match
    regular_match = regular_pattern.search(video_id)
    if regular_match:
        return regular_match.group(1)

    # Check for Shorts video ID match
    shorts_match = shorts_pattern.search(video_id)
    if shorts_match:
        return shorts_match.group(1)

    # If no match found
    return None


@app.route('/contact')
def contact():
    return render_template('contact.html')



#AUTHENTICATED USERS CODE

CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'

#app = flask.Flask(__name__)



def get_authenticated_user_channel_id(credentials):
    youtube = googleapiclient.discovery.build(API_SERVICE_NAME, API_VERSION, credentials=credentials)
    channels_response = youtube.channels().list(
        part='snippet',
        mine=True
    ).execute()
    channel_id = channels_response['items'][0]['id']
    return channel_id

# Create a new function to fetch channel information
def get_authenticated_user_channel_info(credentials):
    youtube = googleapiclient.discovery.build(API_SERVICE_NAME, API_VERSION, credentials=credentials)
    channels_response = youtube.channels().list(
        part='snippet, statistics',
        mine=True
    ).execute()

    print(channels_response)  # Print the response for debugging
    channel_info = {
        'channel_name': channels_response['items'][0]['snippet']['title'],
        'channel_logo': channels_response['items'][0]['snippet']['thumbnails']['default']['url'],  # Get default thumbnail URL
        'description': channels_response['items'][0]['snippet']['description'],
        'subscribers_count': int(channels_response['items'][0]['statistics']['subscriberCount']),
        'videos_count': int(channels_response['items'][0]['statistics']['videoCount']),
        'views_count': int(channels_response['items'][0]['statistics']['viewCount']) if 'statistics' in channels_response['items'][0] else 0,
        'joined_date': channels_response['items'][0]['snippet']['publishedAt'],
        'country': channels_response['items'][0]['snippet']['country']
    }

    return channel_info


def get_video_comments(credentials, video_id):
    youtube = googleapiclient.discovery.build(API_SERVICE_NAME, API_VERSION, credentials=credentials)
    comments = youtube.commentThreads().list(
        part='snippet',
        videoId=video_id,
        maxResults=100
    ).execute()

    comment_texts = [comment['snippet']['topLevelComment']['snippet']['textDisplay'] for comment in comments['items']]
    return comment_texts

def analyze_sentiment(comments):
    positive_count = 0
    neutral_count = 0
    negative_count = 0

    for comment in comments:
        analysis = TextBlob(comment)
        polarity = analysis.sentiment.polarity
        if polarity > 0:
            positive_count += 1
        elif polarity == 0:
            neutral_count += 1
        else:
            negative_count += 1

    return positive_count, neutral_count, negative_count

@app.route('/user_dashboard')
def user_dashboard():
    if 'credentials' not in flask.session:
        return flask.redirect('authorize')

    credentials = google.oauth2.credentials.Credentials(**flask.session['credentials'])
    channel_info = get_authenticated_user_channel_info(credentials)

    return flask.render_template('user_dashboard.html', channel_info=channel_info)


@app.route('/user_videos')
def test_api_request():
    if 'credentials' not in flask.session:
        return flask.redirect('authorize')

    credentials = google.oauth2.credentials.Credentials(**flask.session['credentials'])
    user_channel_id = get_authenticated_user_channel_id(credentials)
    channel_info = get_authenticated_user_channel_info(credentials)

    youtube = googleapiclient.discovery.build(API_SERVICE_NAME, API_VERSION, credentials=credentials)

    videos = youtube.search().list(
        part='snippet',
        channelId=user_channel_id,
        type='video'
    ).execute()

    # video_ids = [video['id']['videoId'] for video in videos['items']]
    # return flask.render_template('user_videos.html', video_ids=video_ids)
    # Extract video titles and IDs
    video_info = [{'title': video['snippet']['title'], 'id': video['id']['videoId']} for video in videos['items']]

    return flask.render_template('user_videos.html', videos=video_info, channel_info=channel_info)

@app.route('/analyze_video/<video_id>')
def analyze_video(video_id):
    if 'credentials' not in flask.session:
        return flask.redirect('authorize')

    credentials = google.oauth2.credentials.Credentials(**flask.session['credentials'])
    channel_info = get_authenticated_user_channel_info(credentials)
    comments = get_video_comments(credentials, video_id)
    positive_comments, neutral_comments, negative_comments = analyze_sentiment(comments)

    return flask.render_template('video_analysis.html', video_id=video_id,
                                 positive_comments=positive_comments, neutral_comments=neutral_comments,
                                 negative_comments=negative_comments,channel_info=channel_info)

@app.route('/authorize')
def authorize():
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES)
    flow.redirect_uri = flask.url_for('oauth2callback', _external=True)

    authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
    flask.session['state'] = state

    return flask.redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    state = flask.session['state']
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
    flow.redirect_uri = flask.url_for('oauth2callback', _external=True)

    authorization_response = flask.request.url
    flow.fetch_token(authorization_response=authorization_response)

    credentials = flow.credentials
    flask.session['credentials'] = credentials_to_dict(credentials)

    return flask.redirect(flask.url_for('user_dashboard'))

@app.route('/revoke')
def revoke():
    if 'credentials' not in flask.session:
        return ('You need to <a href="/authorize">authorize</a> before ' +
                'testing the code to revoke credentials.')

    credentials = google.oauth2.credentials.Credentials(**flask.session['credentials'])

    revoke = requests.post('https://oauth2.googleapis.com/revoke',
        params={'token': credentials.token},
        headers={'content-type': 'application/x-www-form-urlencoded'})

    status_code = getattr(revoke, 'status_code')
    if status_code == 200:
        return 'Credentials successfully revoked.'
    else:
        return 'An error occurred.'

@app.route('/clear')
def clear_credentials():
    if 'credentials' in flask.session:
        del flask.session['credentials']
    return 'Credentials have been cleared.'

def credentials_to_dict(credentials):
    return {'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes}

@app.route('/logout')
def logout():
    session.clear()  # Clear the session
    return redirect(url_for('home'))  # Redirect to the login page

if __name__ == ('__main__'):
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    app.run('localhost', 5000, debug=True)




# if __name__ == '__main__':
#     app.run(debug=True)
