# Data Modeling

Brubeck uses [DictShield](https://github.com/j2labs/dictshield) for modeling. 

DictShield offers input validation and structuring without taking a stance on what database you should be using. There are many good reasons to use all kinds of databases. DictShield only cares about Python dictionaries. If you can get your data into those, DictShield will handle the rest. 

DictShield strives to be database agnostic in the same way that Mongrel2 is language agnostic.

* [DictShield](https://github.com/j2labs/dictshield)


## A Look At The Code

Let's say we're going to store a BlogPost and all of it's comments in a single structure. Maybe we'll even keep a copy of the author information there too.

An `Author` will have some information we only want to share with the author, like the email address associated with a post. But we want every user to be able to see the author's username and name, so those will be public fields.

    class Author(EmbeddedDocument):
        name = StringField()
        username = StringField()
        email = EmailField()
        a_setting = BooleanField()  # private
        is_active = BooleanField()  # private
        _private_fields=['is_active']
        _public_fields=['username', 'name']
    
A `Comment` will contain the comment text, username and email address of the commenter. We only show the email address to the owner of the blog though, so it's not listedd as a public field.

    class Comment(EmbeddedDocument):
        text = StringField()
        username = StringField()
        email = EmailField()   
        _public_fields=['username', 'text']

And now the `BlogPost`. It will have a title, content, author, a post date, the list of comments, and a flag for whether or not it's a deleted entry (eg. a *tombstone*).

    class BlogPost(Document):
        title = StringField()    
        content = StringField()
        author = EmbeddedDocumentField(Author)
        post_date = DateTimeField(default=datetime.datetime.now)
        comments = ListField(EmbeddedDocumentField(Comment))
        deleted = BooleanField()   
        _private_fields=['personal_thoughts']
        _public_fields=['author', 'content', 'comments']
    
Notice that the `BlogPost` has a `ListField` containing a list of `Comments` objects. It also has an `EmbededDocumentField` anytime it's using another DictShield model as the field's value.


## Using It

This is what it might look to instantiate the structures.

    >>> author = Author(name='james', username='j2d2', email='jdennis@gmail.com',
    ...                 a_setting=True, is_active=True)
    >>> comment1 = Comment(text='This post was awesome!', username='bro',
    ...                    email='bru@dudegang.com')
    >>> comment2 = Comment(text='This post is ridiculous', username='barbie',
    ...                    email='barbie@dudegang.com')
    >>> content = """Retro single-origin coffee chambray stumptown, scenester VHS
    ... bicycle rights 8-bit keytar aesthetic cosby sweater photo booth. Gluten-free
    ... trust fund keffiyeh dreamcatcher skateboard, williamsburg yr salvia tattooed
    ... """
    >>> blogpost = BlogPost(title='Hipster Hodgepodge', author=author, content=content,
    ...                     comments=[comment1, comment2], deleted=False)
    
We'd probably call `to_python()` to make the data suitable for saving in a database. This process converts the values exactly as they're found into a dictionary of Python values.

    >>> blogpost.to_python()
    {
        '_types': ['BlogPost'], 
        '_cls': 'BlogPost'
        'post_date': datetime.datetime(2012, 4, 22, 13, 6, 50, 530609), 
        'deleted': False, 
        'title': u'Hipster Hodgepodge', 
        'content': u'Retro single-origin coffee chambray stumptown, scenester VHS\nbicycle rights 8-bit keytar aesthetic cosby sweater photo booth. Gluten-free\ntrust fund keffiyeh dreamcatcher skateboard, williamsburg yr salvia tattooed\n', 
        'author': {
            'username': u'j2d2', 
            '_types': ['Author'], 
            'name': u'james', 
            'a_setting': True, 
            'is_active': True, 
            '_cls': 'Author', 
            'email': u'jdennis@gmail.com'
        }, 
        'comments': [
            {
                'username': u'bro',
                'text': u'This post was awesome!', 
                '_types': ['Comment'], 
                'email': u'bru@dudegang.com', 
                '_cls': 'Comment'
            },
            {
                'username': u'barbie', 
                'text': u'This post is ridiculous', 
                '_types': ['Comment'], 
                'email': u'barbie@dudegang.com', 
                '_cls': 'Comment'
            }
        ], 
    }
    
DictShield also has the concept of an owner formalized in the `make_*_ownersafe()` function, which can serialize to either Python or JSON. Notice that the date is converted to [iso8601 format](http://en.wikipedia.org/wiki/ISO_8601) too.
    
    >>> BlogPost.make_json_ownersafe(blogpost)
    {
        "post_date": "2012-04-22T13:06:50.530609", 
        "deleted": false, 
        "title": "Hipster Hodgepodge", 
        "content": "Retro single-origin coffee chambray stumptown, scenester VHS\nbicycle rights 8-bit keytar aesthetic cosby sweater photo booth. Gluten-free\ntrust fund keffiyeh dreamcatcher skateboard, williamsburg yr salvia tattooed\n"
        "author": {
            "username": "j2d2", 
            "a_setting": true, 
            "name": "james", 
            "email": "jdennis@gmail.com"
        }, 
        "comments": [
            {
                "username": "bro",
                "text": "This post was awesome!", 
                "email": "bru@dudegang.com"
            }, 
            {
                "username": "barbie", 
                "text": "This post is ridiculous", 
                "email": "barbie@dudegang.com"
            }
        ],
    }

This is what the document looks like serialized for the general public. The same basic mechanism is at work as the other serilializations, but this has removed the data that is not for public consumption, like email addresses.

    >>> BlogPost.make_json_publicsafe(blogpost)
    {
        "content": "Retro single-origin coffee chambray stumptown, scenester VHS\nbicycle rights 8-bit keytar aesthetic cosby sweater photo booth. Gluten-free\ntrust fund keffiyeh dreamcatcher skateboard, williamsburg yr salvia tattooed\n"
        "author": {
            "username": "j2d2", 
            "name": "james"
        }, 
        "comments": [
            {
                "username": "bro", 
                "text": "This post was awesome!"
            }, 
            {
                "username": "barbie", 
                "text": "This post is ridiculous"
            }
        ],
    } 
    
Notice that in all of these cases, the permissions and the serialization was done recursively across the structures and embedded structures.


