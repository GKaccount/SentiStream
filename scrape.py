import pandas as pd
import warnings
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from datetime import datetime
import time
import os
import nltk
from wordcloud import WordCloud, STOPWORDS

nltk.downloader

nltk.data.path.append("/opt/render/nltk_data")
nltk.download('vader_lexicon', download_dir="/opt/render/nltk_data", quiet=True, halt_on_error=False)


from nltk.sentiment.vader import SentimentIntensityAnalyzer
from tqdm import tqdm

api_key = 'your_api_key'

# creating YouTube resource object
youtube = build('youtube', 'v3', developerKey=api_key)
warnings.filterwarnings('ignore')

sia = SentimentIntensityAnalyzer()


def video_comments(video_id):
    # empty list for storing reply
    # replies = []
    comments = []

    # retrieve youtube video results
    try:
        video_response = youtube.commentThreads().list(
            part='snippet',
            videoId=video_id,
            order='relevance',
            maxResults=100
        ).execute()
        # extracting required info
        # from each result object
        for item in video_response['items']:
            # Extracting comments
            comment = item['snippet']['topLevelComment']['snippet']
            replyCount = item['snippet']['totalReplyCount']
            comments.append([
                comment['authorDisplayName'],
                comment['textOriginal'],
                comment['likeCount'],
                replyCount
            ])
        # iterate video response
        while 1 == 1:
            try:
                video_response['nextPageToken']
            except KeyError:
                break
            if len(comments) > 100:
                break
            else:
                nextPageToken = video_response['nextPageToken']
                # create a new request object for next page token
                nextRequest = youtube.commentThreads().list(
                    part="snippet",
                    videoId=video_id,
                    order='relevance',
                    maxResults=100,
                    pageToken=nextPageToken
                )
                # Execute the next request
                video_response = nextRequest.execute()
                # Get the comments from next response
                for item in video_response['items']:
                    # Extracting comments
                    comment = item['snippet']['topLevelComment']['snippet']
                    replyCount = item['snippet']['totalReplyCount']
                    comments.append([
                        comment['authorDisplayName'],
                        comment['textDisplay'],
                        comment['likeCount'],
                        replyCount
                    ])
        df = pd.DataFrame(comments, columns=['Author', 'Comment', 'LikeCount', 'ReplyCount'])
        # df.info()
        df.drop_duplicates(subset=['Author', 'Comment'])
        return df
    except HttpError:
        return None


def get_video_stats(video_id):
    # Get video stats
    video_response = youtube.videos().list(
        part='snippet, statistics',
        id=video_id
    ).execute()
    videoTitle = video_response['items'][0]['snippet']['title']
    channelName = video_response['items'][0]['snippet']['channelTitle']
    publishedAt = video_response['items'][0]['snippet']['publishedAt']
    datetime_obj = datetime.strptime(publishedAt, '%Y-%m-%dT%H:%M:%SZ')
    publishedAt = datetime_obj.date().strftime('%d-%m-%Y')
    dct = video_response['items'][0]['statistics']
    dct = list(dct.keys())
    if 'likeCount' in dct:
        likeCount = video_response['items'][0]['statistics']['likeCount']
    else:
        likeCount = None

    if 'commentCount' in dct:
        commentCount = video_response['items'][0]['statistics']['commentCount']
    else:
        commentCount = None

    # view = video_response['items'][0]['statistics']
    if 'viewCount' in dct:
        viewCount = video_response['items'][0]['statistics']['viewCount']
    else:
        viewCount = None
    # thumbnailURL = video_response['items'][0]['snippet']['thumbnails']['maxres']['url']
    videoDetails = {
        'Title': videoTitle,
        'ChannelName': channelName,
        'Views': viewCount,
        'Likes': likeCount,
        'TotalComments': commentCount,
        'PublishedAt': publishedAt,
        # 'ThumbnailURL': thumbnailURL
    }
    lst = []
    for i in videoDetails.values():
        lst.append(i)
    return lst


def sentiment_analyzer(df, file_name):
    result = {}
    for i, row in tqdm(df.iterrows(), total=len(df)):
        text = df['Comment'][i]
        Author = df['Author'][i]
        try:
            score = sia.polarity_scores(text)
            time.sleep(0.05)
            scores = {**score}
            result[Author] = scores
        except RuntimeError:
            print(f'Broke for Author "{Author}" because long data')
            continue

    sentiments_df = pd.DataFrame(result).T.reset_index().rename(columns={'index': 'Author'})
    result_df = pd.merge(df, sentiments_df, on='Author')

    result_df['Label'] = result_df.apply(lambda row1: 'Positive' if row1['compound'] > 0 else (
        'Negative' if row1['compound'] < -0.5 else 'Neutral'), axis=1)

    dir_path = "static"
    file_path = os.path.join(dir_path, file_name + ".csv")

    result_df.to_csv(file_path, index=False)
    return result_df, file_path


def generate_cloud(comments):
    all_text = ' '.join(comments)

    stop_words = set(STOPWORDS)

    wordcloud = WordCloud(width=600, height=300, background_color='black',
                          stopwords=stop_words).generate(all_text)

    return wordcloud
