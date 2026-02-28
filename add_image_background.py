import ffmpeg
import os

# --- Configuration ---
chemin_ffmpeg = r"C:\ffmpeg\bin"
video_input_path = "output/result.mp4"
image_input_path = "input/background.jpeg"
output_path = "output/final.mp4"

os.environ["PATH"] += os.pathsep + chemin_ffmpeg


def add_image_background():
    if not os.path.exists(video_input_path):
        print(f"Error: File {video_input_path} not found.")
        return
    if not os.path.exists(image_input_path):
        print(f"Error: File {image_input_path} not found.")
        return

    # 1. Get original image dimensions using ffprobe
    try:
        probe = ffmpeg.probe(image_input_path)
        video_stream = next(s for s in probe["streams"] if s["codec_type"] == "video")
        img_w = int(video_stream["width"])
        img_h = int(video_stream["height"])
    except ffmpeg.Error as e:
        print("Error probing image:", e.stderr)
        return

    # 2. Calculate target dimensions
    target_w = img_w
    target_h = img_h

    # Only scale down if the image is strictly larger than 1280x720
    if img_w > 1280 or img_h > 720:
        ratio = min(1280 / img_w, 720 / img_h)
        target_w = int(img_w * ratio)
        target_h = int(img_h * ratio)

    # Make sure dimensions are even numbers (required by libx264 for yuv420p)
    target_w = target_w - (target_w % 2)
    target_h = target_h - (target_h % 2)

    print(f"Original image size: {img_w}x{img_h}.")
    print(f"Final video size: {target_w}x{target_h}.")

    # 3. Build FFmpeg Graph
    input_image = ffmpeg.input(image_input_path, loop=1, framerate=1).filter(
        "scale", target_w, target_h
    )

    # Extract only the audio stream from the generated video
    input_audio = ffmpeg.input(video_input_path).audio

    print("Encoding final video...")
    output = ffmpeg.output(
        input_image,
        input_audio,
        output_path,
        vcodec="libx264",
        acodec="copy",  # Optimization: Audio is copied, not re-encoded
        tune="stillimage",  # Optimization: Specific parameters for static image
        preset="ultrafast",
        shortest=None,  # Stops the video when the audio track ends
        pix_fmt="yuv420p",  # Ensures standard colorspace compatibility
    )

    try:
        output.run(overwrite_output=True)
        print(f"Success! Saved to {output_path}")
    except ffmpeg.Error as e:
        print("FFmpeg Error:", e.stderr.decode("utf8") if e.stderr else "Unknown error")


if __name__ == "__main__":
    add_image_background()
