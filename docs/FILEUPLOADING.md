# File Uploading

Brubeck supports file uploading as form-urlencoded or as multipart form data.
It's easy to upload a file to Brubeck using curl.

    $ cd brubeck/demos
    $ ./demo_multipart.py
    
In this demo we see code that finds each file uploaded in a field on the
request message. That looks like this:

    class UploadHandler(...):
        def post(self):
            file_one = self.message.files['data'][0]
            i = Image.open(StringIO.StringIO(file_one['body']))
            i.save('word.png')
            ...
    
This demo receives an image and writes it to the file system as `word.png`. It
wouldn't be much work to adjust this to whatever your needs are.

The demo also uses PIL, so install that if you don't already have it.

    $ pip install PIL
    
Use sudo if necessary.


## Trying It
    
If you're using Mongrel2, you'll need to turn that on too. It works fine with
WSGI too.

    $ m2sh load -db the.db -config mongrel2.conf
    $ m2sh start -db the.db -every
    
OK. Now we can use curl to upload some image.

    $ curl -F data=@someimage.png http://localhost:6767/
    
The end result is that you'll have an image called `word.png` written to the
same directory as your Brubeck process.

