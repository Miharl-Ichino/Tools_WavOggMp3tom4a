#!/usr/bin/env python3
"""
Streamlit音声ファイル変換アプリ
WAV、OGG、MP3ファイルをM4A形式に変換するWebアプリケーション
"""

import streamlit as st
import os
import tempfile
import subprocess
import zipfile
from pathlib import Path
import io

def check_ffmpeg():
    """FFmpegがインストールされているかチェック"""
    ffmpeg_paths = [
        'ffmpeg',  # システムPATH
        '../ffmpeg.exe',  # 一つ上の階層（Windows）
        '../ffmpeg',  # 一つ上の階層（Linux/Mac）
        '../ffmpeg/bin/ffmpeg.exe',  # 一つ上の階層のbinフォルダ（Windows）
        '../ffmpeg/bin/ffmpeg',  # 一つ上の階層のbinフォルダ（Linux/Mac）
    ]
    
    for ffmpeg_path in ffmpeg_paths:
        try:
            subprocess.run([ffmpeg_path, '-version'], capture_output=True, check=True)
            return ffmpeg_path
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    
    return None

def convert_to_m4a(input_file_path, output_dir, quality="192k", ffmpeg_path="ffmpeg"):
    """
    音声ファイルをM4A形式に変換
    
    Args:
        input_file_path (str): 入力ファイルパス
        output_dir (str): 出力ディレクトリ
        quality (str): 音質設定
        ffmpeg_path (str): ffmpegの実行パス
    
    Returns:
        tuple: (成功フラグ, 出力ファイルパス, エラーメッセージ)
    """
    try:
        input_path = Path(input_file_path)
        output_path = Path(output_dir) / f"{input_path.stem}.m4a"
        
        # FFmpegコマンドを構築
        cmd = [
            ffmpeg_path,
            '-i', str(input_path),      # 入力ファイル
            '-c:a', 'aac',              # AACコーデック
            '-b:a', quality,            # ビットレート
            '-movflags', '+faststart',  # ストリーミング最適化
            '-y',                       # 上書き確認なし
            str(output_path)            # 出力ファイル
        ]
        
        # FFmpegを実行
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        
        if result.returncode == 0:
            return True, str(output_path), None
        else:
            return False, None, result.stderr
        
    except Exception as e:
        return False, None, str(e)

def create_zip_file(file_paths, zip_name="converted_files.zip"):
    """複数のファイルをZIPファイルにまとめる"""
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in file_paths:
            if os.path.exists(file_path):
                zip_file.write(file_path, os.path.basename(file_path))
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

def main():
    st.set_page_config(
        page_title="音声ファイル変換アプリ",
        page_icon="🎵",
        layout="wide"
    )
    
    st.title("🎵 音声ファイル変換アプリ")
    st.markdown("WAV、OGG、MP3ファイルをM4A形式に変換します")
    
    # サイドバーで設定
    st.sidebar.header("変換設定")
    
    # 音質設定
    quality_options = {
        "128k": "128 kbps (標準)",
        "192k": "192 kbps (高品質)",
        "256k": "256 kbps (最高品質)",
        "320k": "320 kbps (最高品質+)"
    }
    
    quality = st.sidebar.selectbox(
        "音質設定",
        options=list(quality_options.keys()),
        format_func=lambda x: quality_options[x],
        index=1  # 192kをデフォルトに
    )
    
    # FFmpegの確認
    if 'ffmpeg_checked' not in st.session_state:
        st.session_state.ffmpeg_checked = False
        st.session_state.ffmpeg_path = None
    
    if not st.session_state.ffmpeg_checked:
        with st.spinner("FFmpegを確認中..."):
            ffmpeg_path = check_ffmpeg()
            st.session_state.ffmpeg_path = ffmpeg_path
            st.session_state.ffmpeg_checked = True
    
    if not st.session_state.ffmpeg_path:
        st.error("❌ FFmpegが見つかりません")
        st.markdown("""
        **FFmpegをインストールしてください:**
        - Windows: https://ffmpeg.org/download.html
        - macOS: `brew install ffmpeg`
        - Ubuntu: `sudo apt install ffmpeg`
        """)
        return
    
    st.success(f"✅ FFmpegが見つかりました: {st.session_state.ffmpeg_path}")
    
    # ファイルアップロード
    st.header("📁 ファイルアップロード")
    
    uploaded_files = st.file_uploader(
        "音声ファイルを選択してください",
        type=['wav', 'ogg', 'mp3'],
        accept_multiple_files=True,
        help="WAV、OGG、MP3ファイルを選択できます（複数選択可能）"
    )
    
    if uploaded_files:
        st.success(f"📂 {len(uploaded_files)} ファイルが選択されました")
        
        # ファイル情報を表示
        for i, file in enumerate(uploaded_files):
            st.write(f"**{i+1}.** {file.name} ({file.size:,} bytes)")
        
        # 変換開始ボタン
        if st.button("🚀 変換開始", type="primary"):
            convert_files(uploaded_files, quality, st.session_state.ffmpeg_path)

def convert_files(uploaded_files, quality, ffmpeg_path):
    """ファイル変換を実行"""
    
    # 一時ディレクトリを作成
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_input_dir = Path(temp_dir) / "input"
        temp_output_dir = Path(temp_dir) / "output"
        temp_input_dir.mkdir()
        temp_output_dir.mkdir()
        
        # プログレスバーを初期化
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        converted_files = []
        errors = []
        
        total_files = len(uploaded_files)
        
        for i, uploaded_file in enumerate(uploaded_files):
            # 進捗更新
            progress = (i + 1) / total_files
            progress_bar.progress(progress)
            status_text.text(f"変換中: {uploaded_file.name} ({i+1}/{total_files})")
            
            try:
                # 一時ファイルに保存
                input_file_path = temp_input_dir / uploaded_file.name
                with open(input_file_path, "wb") as f:
                    f.write(uploaded_file.read())
                
                # 変換実行
                success, output_path, error_msg = convert_to_m4a(
                    str(input_file_path),
                    str(temp_output_dir),
                    quality,
                    ffmpeg_path
                )
                
                if success:
                    converted_files.append(output_path)
                    st.success(f"✅ {uploaded_file.name} → {Path(output_path).name}")
                else:
                    errors.append(f"❌ {uploaded_file.name}: {error_msg}")
                    st.error(f"❌ {uploaded_file.name} の変換に失敗しました")
                
            except Exception as e:
                error_msg = f"❌ {uploaded_file.name}: {str(e)}"
                errors.append(error_msg)
                st.error(error_msg)
        
        # 結果表示
        status_text.text("変換完了!")
        
        st.header("📊 変換結果")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("成功", len(converted_files))
        with col2:
            st.metric("失敗", len(errors))
        
        # エラーがあった場合は表示
        if errors:
            st.subheader("❌ エラーファイル")
            for error in errors:
                st.write(error)
        
        # ダウンロード
        if converted_files:
            st.header("📥 ダウンロード")
            
            if len(converted_files) == 1:
                # 単一ファイルの場合
                with open(converted_files[0], "rb") as f:
                    st.download_button(
                        label="📁 変換ファイルをダウンロード",
                        data=f.read(),
                        file_name=os.path.basename(converted_files[0]),
                        mime="audio/mp4"
                    )
            else:
                # 複数ファイルの場合はZIPで
                zip_data = create_zip_file(converted_files)
                st.download_button(
                    label=f"📦 全ファイルをZIPでダウンロード ({len(converted_files)} ファイル)",
                    data=zip_data,
                    file_name="converted_audio_files.zip",
                    mime="application/zip"
                )

if __name__ == "__main__":
    main()