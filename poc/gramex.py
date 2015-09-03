import config

# The global conf holds the current configuration
conf = config.load()

if __name__ == '__main__':
    # Just dump the loaded configuration for testing
    import yaml
    from orderedattrdict import AttrDictYAMLDumper

    print(yaml.dump(conf, Dumper=AttrDictYAMLDumper, default_flow_style=False))
