import ffmpeg
import random
import os

# --- Configuration ---
chemin_ffmpeg = r"C:\ffmpeg\bin"
audio_path_template = "input/t{}.wav"
multiple_audio = "13a5867294bc"
random_order = True
output_path = "output/result.mp4"
video_duration = 60 * 60
occurrences = 14
min_gap = 60

os.environ["PATH"] += os.pathsep + chemin_ffmpeg


def generate_video():
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if random_order:
        random.shuffle(multiple_audio)

    if multiple_audio:
        audio_paths = [audio_path_template.format(e) for e in multiple_audio]
    else:
        audio_paths = [audio_path_template.replace("{}", "")]

    available_sounds = {}
    for p in audio_paths:
        if not os.path.exists(p):
            print(f"Erreur : Le fichier {p} est introuvable.")
            return

        try:
            probe = ffmpeg.probe(p)
            audio_info = next(s for s in probe["streams"] if s["codec_type"] == "audio")
            available_sounds[p] = float(audio_info["duration"])
        except ffmpeg.Error as e:
            print("Erreur lors de l'analyse du fichier audio :", e.stderr)
            return

    sound_keys = list(available_sounds.keys())
    chosen_audio_paths = [sound_keys[i % len(sound_keys)] for i in range(occurrences)]
    sound_duration_extend = [available_sounds[p] for p in chosen_audio_paths]

    total_fixed_time = sum(sound_duration_extend) + ((occurrences - 1) * min_gap)
    free_time = video_duration - total_fixed_time
    gaps = [duration + min_gap for duration in sound_duration_extend]

    if free_time < 0:
        if occurrences > 1:
            max_possible_gap = (video_duration - sum(sound_duration_extend)) / (
                occurrences - 1
            )
            print(
                f"Erreur : Impossible de placer {occurrences} sons avec cet espacement.\n"
                f"Le 'min_gap' est trop grand. Le maximum possible est de : {max_possible_gap:.2f}s."
            )
        else:
            print("Erreur : La vidéo est trop courte pour contenir le son.")
        return

    raw_random_times = sorted(
        [random.uniform(0, free_time) for _ in range(occurrences)]
    )

    delays_ms = [
        int((raw_random_times[i] + sum(gaps[:i])) * 1000) for i in range(occurrences)
    ]

    print(f"Génération du graphe FFmpeg pour {occurrences} sons...")
    print(f"Timestamps prévus : {[round(d/1000, 2) for d in delays_ms]}s")

    rep = input("Génération de la vidéo avec ceux-là ? (y/n)\n>>> ")
    if rep.lower() != "y":
        return

    input_video = ffmpeg.input(
        f"color=c=black:s=1280x720:d={video_duration}", f="lavfi"
    )

    input_audios = [ffmpeg.input(p) for p in chosen_audio_paths]
    base_silence = ffmpeg.input("anullsrc", f="lavfi", t=video_duration)

    audio_streams = [base_silence]

    if len(delays_ms) != len(input_audios):
        print("Erreur : Les gaps ne sont pas autant que les inputs audios.")
        return

    for i in range(len(delays_ms)):
        delayed = input_audios[i].filter("adelay", f"{delays_ms[i]}|{delays_ms[i]}")
        audio_streams.append(delayed)

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
