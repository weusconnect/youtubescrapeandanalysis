import streamlit as st
import pandas as pd
import os
import requests
import yt_dlp as yt_dlp
from googleapiclient.discovery import build
from openai import OpenAI
from openpyxl import load_workbook
import logging
import re 
from pydub import AudioSegment  # Audio splitting

# Initialize OpenAI client
# client = OpenAI(api_key=OPENAI_API_KEY)
log_file = "log.txt"
logging.basicConfig(filename=log_file, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def log_message(message):
    """Logs and displays messages in Streamlit."""
    logging.info(message)
    st.write(message)

# Function to sanitize filenames
def sanitize_filename(file_name):
    file_name = str(file_name)  # Ensure it's a string
    file_name = file_name.replace("/", "").replace("⧸", "")  # Remove only slashes
    return file_name

# Function to rename files inside a folder
def rename_files_in_folder(folder_path):
    if not os.path.exists(folder_path):
        print(f"Folder not found: {folder_path}")
        return

    for file in os.listdir(folder_path):
        old_file_path = os.path.join(folder_path, file)
        
        # Ensure it's a file (not a directory)
        if os.path.isfile(old_file_path):
            # Get file extension
            file_name, file_ext = os.path.splitext(file)
            
            # Sanitize only the filename (keep extension)
            sanitized_name = sanitize_filename(file_name)
            new_file_path = os.path.join(folder_path, f"{sanitized_name}{file_ext}")

            # Rename only if necessary
            if old_file_path != new_file_path:
                os.rename(old_file_path, new_file_path)
                print(f"Renamed: {old_file_path} → {new_file_path}")
            else:
                print(f"No change needed: {old_file_path}")

# Function to extract Channel ID from YouTube link
def extract_channel_id(url):
    pattern = r"(?:youtube\.com/(?:channel/|user/|c/|@|.*[?&]channel_id=))([A-Za-z0-9_-]+)"
    match = re.search(pattern, url)
    return match.group(1) if match else None

# Function to extract video ID from a YouTube URL
def extract_video_id(url):
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(pattern, url)
    return match.group(1) if match else None

# Function to get channel handle (username) from channel ID
def get_channel_handle(channel_id):
    url = f"https://www.googleapis.com/youtube/v3/channels?part=snippet,customUrl&id={channel_id}&key={YOUTUBE_API_KEY}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        if "items" in data and data["items"]:
            channel_info = data["items"][0]["snippet"]
            handle_name = channel_info.get("customUrl", "@Unknown")  # YouTube handle or "@Unknown"
            return handle_name
    return "@Unknown"

# Function to get detailed video information
def get_video_details(video_id):
    url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics,contentDetails,player,status,topicDetails,recordingDetails,liveStreamingDetails&id={video_id}&key={YOUTUBE_API_KEY}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        if "items" in data and data["items"]:
            video_info = data["items"][0]

            # Extract information from different sections
            snippet = video_info.get("snippet", {})
            statistics = video_info.get("statistics", {})
            content_details = video_info.get("contentDetails", {})
            player = video_info.get("player", {})
            status = video_info.get("status", {})
            topic_details = video_info.get("topicDetails", {})
            recording_details = video_info.get("recordingDetails", {})
            live_details = video_info.get("liveStreamingDetails", {})

            # Get Channel ID
            channel_id = snippet.get("channelId", "N/A")
            # Fetch Channel Handle Name
            handle_name = get_channel_handle(channel_id)

            # Convert topic IDs to a readable format
            topics = ", ".join(topic_details.get("topicIds", []))
            relevant_topics = ", ".join(topic_details.get("relevantTopicIds", []))
            topic_categories = ", ".join(topic_details.get("topicCategories", []))

            # Collect video data
            return {
                "Handle Name": handle_name,
                "Channel ID": channel_id,
                "Video ID": video_id,
                "Video Title": snippet.get("title", "N/A"),
                "Video Description": snippet.get("description", "N/A"),
                "Published Date": snippet.get("publishedAt", "N/A"),
                "Channel Name": snippet.get("channelTitle", "N/A"),
                "Category ID": snippet.get("categoryId", "N/A"),
                "Tags": ", ".join(snippet.get("tags", [])) if "tags" in snippet else "N/A",
                "Default Language": snippet.get("defaultLanguage", "N/A"),
                "Audio Language": snippet.get("defaultAudioLanguage", "N/A"),
                "Thumbnail URL": snippet.get("thumbnails", {}).get("high", {}).get("url", "N/A"),
                "View Count": statistics.get("viewCount", "N/A"),
                "Like Count": statistics.get("likeCount", "N/A"),
                "Comment Count": statistics.get("commentCount", "N/A"),
                "Video Duration": content_details.get("duration", "N/A"),
                "Video Quality": content_details.get("definition", "N/A"),
                "3D or 2D": content_details.get("dimension", "N/A"),
                "Captions Available": content_details.get("caption", "N/A"),
                "Licensed Content": content_details.get("licensedContent", "N/A"),
                "Projection Type": content_details.get("projection", "N/A"),
                "Embed HTML": player.get("embedHtml", "N/A"),
                "Privacy Status": status.get("privacyStatus", "N/A"),
                "Upload Status": status.get("uploadStatus", "N/A"),
                "Embeddable": status.get("embeddable", "N/A"),
                "Public Stats Viewable": status.get("publicStatsViewable", "N/A"),
                "Topic IDs": topics,
                "Relevant Topic IDs": relevant_topics,
                "Topic Categories": topic_categories,
                "Recording Date": recording_details.get("recordingDate", "N/A"),
                "Live Start Time": live_details.get("actualStartTime", "N/A"),
                "Live End Time": live_details.get("actualEndTime", "N/A"),
                "Scheduled Live Start": live_details.get("scheduledStartTime", "N/A"),
                "Scheduled Live End": live_details.get("scheduledEndTime", "N/A"),
                "Concurrent Viewers": live_details.get("concurrentViewers", "N/A"),
                "Live Chat ID": live_details.get("activeLiveChatId", "N/A"),
            }
    return None

# Function to format timestamps
def format_time_hms(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    remaining_seconds = seconds % 60
    return f"{hours:02}:{minutes:02}:{int(remaining_seconds):02}" if hours else f"{minutes:02}:{int(remaining_seconds):02}"

# Function to split audio into 60s chunks and return correct start times
def split_audio(file_path, chunk_length_ms=60000):  # Default: 60 seconds per chunk
    audio = AudioSegment.from_mp3(file_path)
    chunks = [audio[i:i + chunk_length_ms] for i in range(0, len(audio), chunk_length_ms)]
    
    chunk_paths = []
    chunk_start_times = []  # Store start times for timestamp correction
    base_name = os.path.splitext(file_path)[0]

    for i, chunk in enumerate(chunks):
        chunk_path = f"{base_name}_part{i}.mp3"
        chunk.export(chunk_path, format="mp3")
        chunk_paths.append(chunk_path)
        chunk_start_times.append(i * (chunk_length_ms / 1000))  # Convert ms to seconds
    
    return chunk_paths, chunk_start_times

###################################################
################### UI Creation ###################
###################################################
# Streamlit App Title
st.title("Flux様 - YouTubeデータスクレーピングとダウンロードアプリ")
st.subheader("🔐 API Key定義", divider=True)
OPENAI_API_KEY = st.text_input("OpenAI API Keyを記入してください", type="password")
YOUTUBE_API_KEY = st.text_input("YouTube API KeyKeyを記入してください", type="password")

# Only initialize OpenAI client if key is provided
if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)
else:
    st.warning("OpenAI API Keyを記入してください")

# File Upload Section
st.subheader("ステップ1：AnnalysisChannel情報のスクレイピング設定", divider=True)
st.markdown("チャンネルハンドルのリストが含まれたファイルを選択してください")
save_folder = st.text_input("データを保存するフォルダのパスを入力してください（例：C:/Users/YourName/Documents/YT_Data）")
uploaded_file = st.file_uploader("YouTubeチャンネルのハンドルが記載されたExcelファイルをアップロードしてください。(eg. @Hunter_Channel, @yo2_man, @metan-car-life)", type=["xlsx"])

if uploaded_file:    
    # Load the Excel file
    df = pd.read_excel(uploaded_file)
    st.subheader("ステップ2：チャンネル情報のスクレイピング", divider=True)
    st.markdown("スクレイピングしてチャンネル情報を生成するYouTubeハンドルのリストが含まれた列を選択してください。")
    column_name = st.selectbox("YouTubeハンドルが含まれる列を選択してください", df.columns)
    ###########################################################################
    ################## Step 1: Channel Data Scraping ##########################
    ###########################################################################
    if st.button("チャンネルデータのスクレイピングを実行"):
        st.write("チャンネルデータを取得中...")

        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        channel_data = []

        for handle in df[column_name].dropna().astype(str).tolist():
            url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={handle}&type=channel&key={YOUTUBE_API_KEY}"
            response = requests.get(url).json()

            if "items" in response and response["items"]:
                channel_id = response["items"][0]["id"]["channelId"]
            else:
                st.warning(f"指定されたハンドルに対応するチャンネルが見つかりませんでした: {handle}")
                continue

            request = youtube.channels().list(
                part="snippet,statistics,brandingSettings,contentDetails",
                id=channel_id
            )
            response = request.execute()

            if "items" in response:
                channel_info = response["items"][0]
                # Extract information from different sections
                snippet = channel_info.get("snippet", {})
                statistics = channel_info.get("statistics", {})
                branding = channel_info.get("brandingSettings", {})
                content_details = channel_info.get("contentDetails", {})
                topic_details = channel_info.get("topicDetails", {})
                localizations = channel_info.get("localizations", {})
                content_owner = channel_info.get("contentOwnerDetails", {})
                status = channel_info.get("status", {})

                # Convert topic IDs to string (list of topics)
                topics = ", ".join(topic_details.get("topicIds", []))
                relevant_topics = ", ".join(topic_details.get("relevantTopicIds", []))

                # Convert localizations to a readable format
                localization_info = "\n".join([
                    f"{lang}: {details.get('title', 'N/A')} - {details.get('description', 'N/A')}" 
                    for lang, details in localizations.items()
                ])

                # Collect all data
                channel_data.append({
                    "Handle": handle,
                    "Channel ID": channel_id,
                    "Channel Title": snippet.get("title", "N/A"),
                    "Channel Description": snippet.get("description", "N/A"),
                    "Published Date": snippet.get("publishedAt", "N/A"),
                    "Country": snippet.get("country", "N/A"),
                    "Subscribers": statistics.get("subscriberCount", "N/A"),
                    "Total Views": statistics.get("viewCount", "N/A"),
                    "Total Videos": statistics.get("videoCount", "N/A"),
                    "Custom URL": snippet.get("customUrl", "N/A"),
                    "Channel Keywords": branding.get("channel", {}).get("keywords", "N/A"),
                    "Analytics Tracking ID": branding.get("channel", {}).get("trackingAnalyticsAccountId", "N/A"),
                    "Trailer Video (Non-Subscribers)": branding.get("channel", {}).get("unsubscribedTrailer", "N/A"),
                    "Default Language": branding.get("channel", {}).get("defaultLanguage", "N/A"),
                    "Banner Image URL": branding.get("image", {}).get("bannerExternalUrl", "N/A"),
                    "Uploads Playlist ID": content_details.get("relatedPlaylists", {}).get("uploads", "N/A"),
                    "Likes Playlist ID": content_details.get("relatedPlaylists", {}).get("likes", "N/A"),
                    "Favorites Playlist ID": content_details.get("relatedPlaylists", {}).get("favorites", "N/A"),
                    "Watch Later Playlist ID": content_details.get("relatedPlaylists", {}).get("watchLater", "N/A"),
                    "Topic IDs": topics,
                    "Relevant Topic IDs": relevant_topics,
                    "Localization Info": localization_info,
                    "Content Owner": content_owner.get("contentOwner", "N/A"),
                    "Time Linked to Content Owner": content_owner.get("timeLinked", "N/A"),
                    "Privacy Status": status.get("privacyStatus", "N/A"),
                    "Is Linked to Google Account": status.get("isLinked", "N/A"),
                    "Long Uploads Status": status.get("longUploadsStatus", "N/A")
                })
            else:
                print(f"チャンネルIDの詳細が見つかりませんでした: {channel_id}")

        channel_data_path = os.path.join(save_folder, "01_YouTube_Channel_Data.xlsx")
        pd.DataFrame(channel_data).to_excel(channel_data_path, index=False)
        st.success(f"チャンネルデータは次の場所に保存されました： {channel_data_path}")
    ###########################################################################
    ################## Step 2: Video Data Scraping ############################
    ###########################################################################
    st.subheader("ステップ3：動画データのスクレイピング", divider=True)
    uploaded_file = st.file_uploader("YouTube動画リンクが記載されたExcelファイルをアップロードしてください", type=["xlsx"])
    if uploaded_file:
        # Excelファイルの読み込み
        df = pd.read_excel(uploaded_file)
        column_name = st.selectbox("YouTubeリンクが含まれる列を選択してください", df.columns)

        # ステップ1：動画データのスクレイピング
        if st.button("動画データのスクレイピングを実行"):
            st.write("動画データを取得中...")
            video_data = []
            youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

            for _, row in df.iterrows():
                video_url = row[column_name]
                if pd.isna(video_url):
                    continue

                video_id = extract_video_id(video_url)
                if not video_id:
                    st.warning(f"指定されたリンクから動画IDを取得できませんでした: {video_url}")
                    continue

                video_stats = get_video_details(video_id)
                if video_stats:
                    video_stats["Video URL"] = video_url  # Add original URL to results
                    video_data.append(video_stats)

            # 🔹 Save Data to Excel
            if save_folder:
                video_data_path = os.path.join(save_folder, "02_YouTube_Video_Data.xlsx")
                pd.DataFrame(video_data).to_excel(video_data_path, index=False)
                st.session_state.video_data_path = video_data_path
                st.success(f"✅ 動画データは次の場所に保存されました: {video_data_path}")
            else:
                st.error("有効なフォルダパスを入力してください。")

    ###########################################################################
    ################### Step 3: Download Videos & Audio #######################
    ###########################################################################
    st.subheader("ステップ4：音声および動画ファイルのダウンロード", divider=True)
    st.markdown("以下のボタンをクリックすると、MP4およびMP3ファイルの生成が始まります。ステップ1で指定したフォルダパスに新しいフォルダが作成されます。")

    # ✅ Ensure `video_data_path` exists before proceeding
    if st.button("MP4とMP3をダウンロード"):
        if not save_folder:
            st.error("❌ 有効なフォルダパスを入力してください。")
            log_message("❌ エラー：保存先フォルダが入力されていません。")
        else:
            video_data_path = os.path.join(save_folder, "02_YouTube_Video_Data.xlsx")

            if not os.path.exists(video_data_path):
                st.error(f"❌ ファイルが見つかりません：{video_data_path}。先に動画スクレイピングを実行してください。")
                log_message(f"❌ エラー：動画データファイルが見つかりません（{video_data_path}）。")
            else:
                log_message("📥 動画と音声のダウンロードを開始します...")

                video_df = pd.read_excel(video_data_path)
                video_ids = video_df["Video ID"].dropna().astype(str).tolist()
                youtube_links = [f"https://www.youtube.com/watch?v={video_id}" for video_id in video_ids]

                video_folder = os.path.join(save_folder, "Video")
                audio_folder = os.path.join(save_folder, "Audio")
                os.makedirs(video_folder, exist_ok=True)
                os.makedirs(audio_folder, exist_ok=True)

                log_message(f"⏳ {len(youtube_links)} 本の動画をダウンロード中...")

                def video_hook(d):
                    if d['status'] == 'finished':
                        log_message(f"✅ 動画のダウンロード完了：{d['filename']}")

                def audio_hook(d):
                    if d['status'] == 'finished':
                        log_message(f"🎵 音声のダウンロード完了：{d['filename']}")

                ydl_opts_video = {
                    'outtmpl': os.path.join(video_folder, f"{sanitize_filename('%(title)s')}.%(ext)s"), ##################
                    'format': 'bestvideo+bestaudio/best',
                    'progress_hooks': [video_hook]
                }
                ydl_opts_audio = {
                    'outtmpl': os.path.join(audio_folder, f"{sanitize_filename('%(title)s')}.%(ext)s"), ##################
                    'format': 'bestaudio/best',
                    'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
                    'progress_hooks': [audio_hook]
                }

                with yt_dlp.YoutubeDL(ydl_opts_video) as ydl:
                    ydl.download(youtube_links)
                log_message("✅ すべての動画のダウンロードが完了しました。")

                with yt_dlp.YoutubeDL(ydl_opts_audio) as ydl:
                    ydl.download(youtube_links)
                log_message("✅ すべての音声（MP3）のダウンロードが完了しました。")
                rename_files_in_folder(video_folder)
                rename_files_in_folder(audio_folder)
                st.session_state.save_folder = save_folder
                st.session_state.audio_folder = audio_folder
                st.session_state.video_folder = video_folder
                st.success(f"🎉 動画は {video_folder} に、MP3は {audio_folder} に保存されました。")
    
##########################################
    # Step 5: Generating Transcripts
    st.subheader("ステップ5：文字起こしの生成", divider=True)
    st.markdown("ボタンをクリックすると、**プレーンテキストの文字起こし** と **タイムスタンプ付きの文字起こし** の2種類が生成されます。")

    if st.button("文字起こしを生成"):
        if not save_folder:
            st.error("❌ 有効なフォルダパスを入力してください。")
        else:
            audio_folder = os.path.join(save_folder, "Audio")
            transcript_folder = os.path.join(save_folder, "Transcript")
            timestamp_transcript_folder = os.path.join(save_folder, "Time Stamp Transcript")

            os.makedirs(transcript_folder, exist_ok=True)
            os.makedirs(timestamp_transcript_folder, exist_ok=True)

            if not os.path.exists(audio_folder):
                st.error(f"❌ 音声フォルダが見つかりません：{audio_folder}。先にMP3ファイルをダウンロードしてください。")
            else:
                st.write("📜 文字起こし処理を開始しています...")

                # Loop through all MP3 files in the folder
                for file_name in os.listdir(audio_folder):
                    if file_name.endswith(".mp3"):
                        file_path = os.path.join(audio_folder, file_name)
                        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)  # Convert bytes to MB
                        
                        st.write(f"⏳ 処理中：{file_name}（{file_size_mb:.2f}MB）")

                        # ファイルサイズが25MBを超える場合は分割
                        if file_size_mb > 25:
                            st.write("🔹 音声ファイルを小さなチャンクに分割しています...")
                            chunk_files, chunk_start_times = split_audio(file_path)
                        else:
                            chunk_files = [file_path]
                            chunk_start_times = [0]  # Start from 0s if no split

                        transcript_text = []
                        data = []

                        # Process each audio chunk
                        for chunk_idx, chunk_file in enumerate(chunk_files):
                            chunk_start_time = chunk_start_times[chunk_idx]

                            with open(chunk_file, "rb") as audio_chunk:
                                try:
                                    transcription_data = client.audio.transcriptions.create(
                                        model="whisper-1",
                                        file=audio_chunk,
                                        response_format="verbose_json"
                                    )
                                    transcription_data = transcription_data.model_dump()
                                except Exception as e:
                                    st.error(f"❌ {chunk_file} の文字起こしでエラーが起きました：{e}")
                                    continue

                            # Extract transcript data
                            if "segments" in transcription_data:
                                for segment in transcription_data["segments"]:
                                    start_time = format_time_hms(segment.get("start", 0) + chunk_start_time)
                                    end_time = format_time_hms(segment.get("end", 0) + chunk_start_time)
                                    text = str(segment.get("text", "N/A"))  # Ensure text is a string

                                    # Handle NaN values
                                    start_time = start_time if start_time else "00:00"
                                    end_time = end_time if end_time else "00:00"

                                    data.append([start_time, end_time, text])
                                    transcript_text.append(text)


                            # Remove chunk files after processing
                            os.remove(chunk_file)

                        # Convert to DataFrame
                        df = pd.DataFrame(data, columns=["Start Time", "End Time", "Text"])

                        # Define output file names
                        base_name = os.path.splitext(file_name)[0]
                        excel_file_path = os.path.join(timestamp_transcript_folder, f"{base_name}_timestamp_transcript.xlsx")
                        text_file_path = os.path.join(transcript_folder, f"{base_name}_transcript.txt")

                        # Save timestamped transcript as an Excel file
                        df.to_excel(excel_file_path, index=False, engine='openpyxl')

                        # Adjust column widths in Excel
                        wb = load_workbook(excel_file_path)
                        ws = wb.active
                        ws.column_dimensions['A'].width = 50 / 7
                        ws.column_dimensions['B'].width = 50 / 7
                        ws.column_dimensions['C'].width = 500 / 7
                        wb.save(excel_file_path)

                        st.write(f"📄 タイムスタンプ付き文字起こしを保存しました：{excel_file_path}")

                # プレーンテキストの文字起こしをテキストファイルとして保存
                with open(text_file_path, "w", encoding="utf-8") as txt_file:
                    for text in transcript_text:
                        txt_file.write(text + "\n")

                st.write(f"📄 プレーンテキストの文字起こしを保存しました：{text_file_path}")

                st.success(f"📜 文字起こしファイルを {transcript_folder} と {timestamp_transcript_folder} に保存しました")
                
    ###########################################################################
    #########################  ✅ Step 7: Show Logs ##########################
    ###########################################################################
    if st.button("ログを表示"):
        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                logs = f.read()
            st.text_area("📄 ログ出力：", logs, height=300)
        else:
            st.warning("⚠ ログファイルが見つかりません。")
