# Ebook Store Project Handoff

## Project Goal
Streamlit app that displays 500 ebooks from Google Drive with covers, all priced at $4.99, with Stripe checkout.

## STORE IS LIVE! 🎉
**URL:** https://ebook-store-sm6epb55uc3xit4mv5iuhu.streamlit.app

## What's Done
- Google Cloud project "Ebook Store" created
- Service account: `ebook-reader@ebook-store-485023.iam.gserviceaccount.com`
- Google Drive API enabled
- Drive folder "PUBLISHED" shared with service account
- Folder ID: `1UB1sOSqQQ53H2piP7CWTS8h7pafGkpqY`
- Stripe connected (live keys)
- GitHub repo: `aipublishingpro-beep/ebook-store`
- Streamlit Cloud deployed with secrets
- Code searches all subfolders for books

## Drive Folder Structure
```
PUBLISHED/
  ├── Book Title/
  │     ├── Book Title.docx
  │     └── Book Title With Subtitle Here.jpg (cover)
  └── ... 500+ folders
```

## What's Left - COVER FIX NEEDED
Current code looks for `Title_cover.jpg` but actual covers are named differently (title with subtitle as .jpg/.png in same folder).

**Fix needed:** Update code to grab ANY .jpg or .png file in the same folder as the .docx instead of matching by name.

## Key Details
- All books $4.99
- Stripe fees: 2.9% + $0.30 per sale (~$4.54 net)
- Cache refreshes hourly (or add `?clear_cache=1` to URL)
- Adding new books: just add folder to PUBLISHED in Drive

## Resume Instructions
User should say: "Let's fix the book covers" and Claude should update the get_all_files() function to match any .jpg/.png in the same subfolder as the .docx file.
