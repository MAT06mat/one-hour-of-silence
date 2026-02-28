import ffmpeg
import random
import os

# --- Configuration ---
chemin_ffmpeg = r"C:\ffmpeg\bin"
audio_path = "input/sound.wav"
output_path = "output/result.mp4"
video_duration = 60 * 60
occurrences = 10
min_gap = 10

os.environ["PATH"] += os.pathsep + chemin_ffmpeg


def generate_video():
    if not os.path.exists(audio_path):
        print(f"Erreur : Le fichier {audio_path} est introuvable.")
        return

    try:
        probe = ffmpeg.probe(audio_path)
        audio_info = next(s for s in probe["streams"] if s["codec_type"] == "audio")
        sound_duration = float(audio_info["duration"])
    except ffmpeg.Error as e:
        print("Erreur lors de l'analyse du fichier audio :", e.stderr)
        return

    # Calculate required times
    total_fixed_time = (occurrences * sound_duration) + ((occurrences - 1) * min_gap)
    free_time = video_duration - total_fixed_time
    gap = sound_duration + min_gap

    if free_time < 0:
        if occurrences > 1:
            max_possible_gap = (video_duration - (occurrences * sound_duration)) / (
                occurrences - 1
            )
            print(
                f"Erreur : Impossible de placer {occurrences} sons avec cet espacement.\n"
                f"Le 'min_gap' est trop grand. Le maximum possible est de : {max_possible_gap:.2f}s."
            )
        else:
            print("Erreur : La vidéo est trop courte pour contenir le son.")
        return

    # Generate random points in the free time space and sort them
    raw_random_times = sorted(
        [random.uniform(0, free_time) for _ in range(occurrences)]
    )

    # Expand the points using the fixed gaps and convert to ms
    delays_ms = [
        int((raw_random_times[i] + (i * gap)) * 1000) for i in range(occurrences)
    ]

    print(f"Génération du graphe FFmpeg pour {occurrences} sons...")
    print(f"Timestamps prévus : {[round(d/1000, 2) for d in delays_ms]}s")

    rep = input("Génération de la vidéo avec ceux-là ? (y/n)\n>>> ")
    if rep.lower() != "y":
        return

    input_video = ffmpeg.input(
        f"color=c=black:s=1280x720:d={video_duration}", f="lavfi"
    )

    input_audio = ffmpeg.input(audio_path)

    # Generate base silence of exact video duration
    base_silence = ffmpeg.input("anullsrc", f="lavfi", t=video_duration)

    # Initialize list with the base silence
    audio_streams = [base_silence]

    # Add delayed sounds
    for delay in delays_ms:
        delayed = input_audio.filter("adelay", f"{delay}|{delay}")
        audio_streams.append(delayed)

    # Mix silence with delayed sounds
    mixed_audio = ffmpeg.filter(
        audio_streams,
        "amix",
        inputs=len(audio_streams),
        dropout_transition=0,
        normalize=0,
    )

    output = ffmpeg.output(
        input_video,
        mixed_audio,
        output_path,
        vcodec="libx264",
        acodec="libmp3lame",
        tune="stillimage",
        preset="ultrafast",
        shortest=None,
    )

    print("Lancement de l'encodage FFmpeg...")
    try:
        output.run(overwrite_output=True)
        print(f"Succès ! Vidéo sauvegardée sous : {output_path}")
    except ffmpeg.Error as e:
        print("Erreur FFmpeg :", e.stderr.decode("utf8"))


if __name__ == "__main__":
    generate_video()
