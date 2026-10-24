import time
import pathlib

t0 = time.time()
pathlib.Path(__file__).parent / "detached_test.txt"
for i in range(6):
    time.sleep(5)
    with open(r"C:\Users\Umar\anime-text-dataset\detached_test.txt", "w") as f:
        f.write(f"alive at {time.time() - t0:.0f}s")
