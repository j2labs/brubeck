# QuerySets

There are times when a carefully crafted query is right and there are times 
when a simple CRUD interface can do the trick. Brubeck provides querysets that
implement a simple CRUD interface. This is useful for the AutoAPI, support for
basic caching and a consistent way of handling database connections.

A `Queryset` is then an implementation of CRUD functions for a single item or
multiple items. This type of interface makes the system consistent with the
idea that data should be stored in a simple manner, eg. a key that maps to a
particular document.

If you need anything more complicated than that, it's easy enough to go from
the DictShield model into something that will fit nicely with your custom
query.

Querysets are an area of active development but are still young in
implementation.
