"""A series of functions to help with the manipulation of DOT files.""" ""
import argparse
import os
import pathlib
from typing import List

import graphviz  # type: ignore
from moviepy.editor import ImageClip, concatenate_videoclips  # type: ignore


class DotFilmStrip:
    name: str
    dot_frames: List[str] = []

    def __init__(self, name: str) -> None:
        self.name = name

    def add_frame(self, dot: str) -> None:
        self.dot_frames.append(dot)

    def clear_frames(self) -> None:
        self.dot_frames.clear()

    def render(self, working_dir: str, duration: int = 600) -> None:
        # validate working directory exists, is a directory, and is empty
        dir = pathlib.Path(working_dir)
        if not dir.exists():
            # create the directory
            dir.mkdir(parents=True)
        if not dir.is_dir():
            raise Exception("Working directory is not a directory")
        if len(list(dir.iterdir())) != 0:
            # Ask user if they want to overwrite the directory
            print(f"Working directory is not empty: {working_dir}")
            for file in os.listdir(working_dir):
                print(f"  - {file}")

            print("Do you want to overwrite the directory? [y/n]")
            overwrite = input()
            if overwrite.lower() == "y":
                # delete all files in the directory
                for file in os.listdir(working_dir):
                    os.remove(os.path.join(working_dir, file))
            else:
                raise Exception("Working directory is not empty")

        # render each frame
        for i, dot_str in enumerate(self.dot_frames):
            dot = graphviz.Source(dot_str)
            dot.render(filename=f"{self.name}-{i}", directory=working_dir, format="png")

        # combine frames into a gif
        gif_name = f"{self.name}.gif"
        gif_path = os.path.join(working_dir, gif_name)

        image_paths = [
            os.path.join(working_dir, img)
            for img in sorted(os.listdir(working_dir))
            if img.endswith(".png")
        ]
        if len(image_paths) == 0:
            raise Exception("No images found in working directory")
        else:
            clips = [ImageClip(m).set_duration(duration) for m in image_paths]
            concat_clip = concatenate_videoclips(clips, method="compose")
            concat_clip.write_gif(gif_path, fps=2)


if __name__ == "__main__":
    # read name and working directory from command line
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "name",
        help="The name of the filmstrip",
        type=str,
    )
    parser.add_argument(
        "dir",
        help="The name of the directory to save the frames to",
        type=str,
        default=".",
    )
    args = parser.parse_args()

    dfs = DotFilmStrip(args.name)
    # dfs.add_frame("digraph { a -> b }")
    # dfs.add_frame("digraph { a -> b -> c }")
    # dfs.add_frame("digraph { a -> b -> c -> d }")
    dfs.render(args.dir)