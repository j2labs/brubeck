# File Uploading

Brubeck supports file uploading as form-urlencoded or as multipart form data.
It's easy to upload a file to Brubeck using curl.

    $ cd brubeck/demos
    $ ./demo_multipart.py
    
If you're using Mongrel2, you'll need to turn that on too. It works fine with
WSGI too.

    $ m2sh load -db the.db -config mongrel2.conf
    $ ms2h start -db the.db -every
    
OK. Now we can use curl to upload some image.

    $ curl -F data=@someimage.png http://localhost:6767/
    
The end result is that you'll have an image called `word.png` written to the
same directory as your Brubeck process.

You're gonna need to install PIL for this demo to work, btw.

    $ pip install PIL
    
Use sudo if necessary.
