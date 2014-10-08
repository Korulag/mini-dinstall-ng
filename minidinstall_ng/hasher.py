import hashlib

standart_hashes
BLOCKSIZE = 65536


def hash_file(filename, hash_type):
    '''
    Returns the hash of a file as hex-digest.
    :param filename: Path to the file
    :param hash_type: Name of the hash algorithm.
    ''' 
    if hash_type in hashlib.algorithms:
        algo = getattr(hashlib, hash_type)
    else:
        algo = hashlib.new(hash_type)
    hasher = algo()
    with open(filename, 'rb') as afile:
        buf = afile.read(BLOCKSIZE)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(BLOCKSIZE)
    return hasher.hexdigest()

