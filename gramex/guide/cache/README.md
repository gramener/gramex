# Caching requests

The `url:` handlers accept a `cache:` key that defines caching behaviour. For
example, this configuration at [random](random) generates random letters every
time it is called:

    random:
        pattern: $YAMLURL/random
        handler: FunctionHandler
        kwargs:
            function: random.choice
            args: [['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']]

But adding the `cache:` to this URL caches it the first time it is called. When
[random-cached](random-cached) is reloaded, the same letter is shown every time.

    random-cached:
        pattern: $YAMLURL/random-cached
        handler: FunctionHandler
        kwargs:
            function: random.choice
            args: [['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']]
        cache: true
