import json

X_OFFSET = 20
Y_OFFSET = 40

with open('config.json', 'r') as f:
    config = json.load(f)

    config['manager'][2][0] += X_OFFSET
    config['manager'][2][1] += Y_OFFSET

    for anchor_config in config['anchors']:
        if len(anchor_config) > 2:
            anchor_config[2][0] += X_OFFSET
            anchor_config[2][1] += Y_OFFSET

    with open('config-new.json', 'w') as ff:
        json.dump(config, ff)
