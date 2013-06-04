def gt(value, threshold):
    return float(value) > float(threshold)

def lt(value, threshold):
    return float(value) < float(threshold)

def eq(value, threshold):
    assert abs(value - threshold) < 0.01
