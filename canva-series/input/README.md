# Preparing the uploaded tutorial image archive

The ZIP is already stored at `canva-series/input/final_24MB.zip`.

The separate **Prepare All Tutorial Images** GitHub Actions workflow safely extracts supported image files, sorts them by filename, and creates:
- `contact-sheet.jpg` — a visual overview of the images
- `manifest.csv` — original filenames, dimensions, and extraction status
- `images/` — extracted, consistently numbered image files
- `SUMMARY.txt` — image counts

## Run it

After this change is merged, open **Actions → Prepare All Tutorial Images → Run workflow**. When it finishes, download the `tutorial-images-prepared` artifact from that run.

This is an input-preparation step only. It does not change the existing Shorts workflow or generate videos yet. The contact sheet and manifest let the full series be organized from the actual screenshots rather than guessing that every fixed number of images is one day.
