Simple SmugMug Upload Script
============================

Instructions:

1. Get a SmugMug account at https://www.smugmug.com/
2. Apply for an API key at http://www.smugmug.com/hack/apikeys
3. Find your API key and secret in Account Settings -> Discovery -> Api Keys
4. Create a .sm_upload in the working directory that looks like this::

  ---
  - PASTE_OF_API_KEY
  - PASTE_OF_API_SECRET

5. Organize photos to be uploaded in Catetories.  For example:
   an image at Categories/Nature/Sunrise/Maui.jpg will be uploaded
   to SmugMug in the Nature category, Sunrise album, named Maui.jpg
6. Run sm_upload.rb, first time it will prompt you to log in to SmugMug 
   and authorize the app. Subsequent times will not prompt again.

Caveats
-------

This uses SmugMug API v1.3, which as of July 2013 if you use the "New" layout
means you cannot create albums correctly (they get created, but always in "Other" 
no matter what). 

This script caches agressively, and expects that you have not uploaded photos 
using other means for the cache to be correct.  If photos have been uploaded
using some other method, make sure to update the cache first to prevent 
duplicate photos in albums


   
