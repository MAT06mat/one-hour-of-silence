import ffmpeg
import os

# --- Configuration ---
chemin_ffmpeg = r"C:\ffmpeg\bin"
video_input_path = "output/result.mp4"
image_input_path = "input/background.png"
output_dir = "output"
video_output_name = "final.mp4"
bg_color = "white"  # Background color ('white', 'black', '#RRGGBB', etc.)

os.environ["PATH"] += os.pathsep + chemin_ffmpeg


def add_image_background():
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if not os.path.exists(video_input_path):
        print(f"Erreur : Fichier {video_input_path} introuvable.")
        return
    if not os.path.exists(image_input_path):
        print(f"Erreur : Fichier {image_input_path} introuvable.")
        return

    final_video_path = os.path.join(output_dir, video_output_name)
    thumbnail_path = os.path.join(output_dir, "thumbnail.jpg")

    # 1. Get original image dimensions using ffprobe
    try:
        probe = ffmpeg.probe(image_input_path)
        video_stream = next(s for s in probe["streams"] if s["codec_type"] == "video")
        img_w = int(video_stream["width"])
        img_h = int(video_stream["height"])
    except ffmpeg.Error as e:
        print("Erreur lors de l'analyse de l'image:", e.stderr)
        return

    # 2. Calculate target dimensions
    target_aspect = 16 / 9

    canvas_w = img_w
    canvas_h = img_h

    if img_w / img_h > target_aspect:
        canvas_h = int(img_w / target_aspect)
    else:
        canvas_w = int(img_h * target_aspect)

    if canvas_w > 1280 or canvas_h > 720:
        canvas_w = 1280
        canvas_h = 720

    ratio = min(canvas_w / img_w, canvas_h / img_h)
    scaled_w = int(img_w * ratio)
    scaled_h = int(img_h * ratio)

    # Make dimensions even (required by libx264)
    canvas_w -= canvas_w % 2
    canvas_h -= canvas_h % 2
    scaled_w -= scaled_w % 2
    scaled_h -= scaled_h % 2

    print(f"Taille d'origine : {img_w}x{img_h}.")
    print(f"Taille redimensionnée : {scaled_w}x{scaled_h}.")
    print(f"Taille finale du canevas 16:9 : {canvas_w}x{canvas_h}.")
    print(f"Couleur de fond / bordures : {bg_color}")

    # 3. Build FFmpeg Graph
    # Load the image
    input_image = ffmpeg.input(image_input_path, loop=1, framerate=1)
    scaled_image = input_image.filter("scale", scaled_w, scaled_h)

    # Generate a solid color background (this handles both padding and PNG transparency)
    background = ffmpeg.input(f"color=c={bg_color}:s={canvas_w}x{canvas_h}", f="lavfi")

    # Overlay the scaled image onto the background
    processed_image = ffmpeg.filter(
        [background, scaled_image], "overlay", x="(W-w)/2", y="(H-h)/2"
    )

    print(f"Génération de la miniature ({thumbnail_path})...")
    thumbnail_stream = (
        processed_image
        # Force the pixel format for standard JPG compatibility
        .output(thumbnail_path, vframes=1, pix_fmt="yuvj420p").overwrite_output()
    )

    try:
        thumbnail_stream.run(capture_stdout=True, capture_stderr=True)
    except ffmpeg.Error as e:
        print("Erreur miniature :", e.stderr.decode("utf8"))

    # Extract only the audio stream from the generated video
    input_audio = ffmpeg.input(video_input_path).audio

    print("Encodage de la vidéo finale...")
    output = ffmpeg.output(
        processed_image,
        input_audio,
        final_video_path,
        vcodec="libx264",
        acodec="copy",  # Optimization: Audio is copied, not re-encoded
        tune="stillimage",  # Optimization: Specific parameters for static image
        preset="ultrafast",
        shortest=None,  # Stops the video when the audio track ends
        pix_fmt="yuv420p",  # Ensures standard colorspace compatibility
    )

    try:
        output.run(overwrite_output=True)
        print(f"Succès ! Vidéo sauvegardée sous : {final_video_path}")
    except ffmpeg.Error as e:
        print(
            "Erreur FFmpeg :",
            e.stderr.decode("utf8") if e.stderr else "Erreur inconnue",
        )


if __name__ == "__main__":
    add_image_background()
