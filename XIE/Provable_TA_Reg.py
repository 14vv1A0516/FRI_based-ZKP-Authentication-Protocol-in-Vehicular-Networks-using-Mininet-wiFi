import socket 
import random    
import pyexcel as pe
import time 
import threading  
import datetime
import threading
import collections 
from hashlib import sha256
from ecies.utils import generate_eth_key
from ecies import encrypt, decrypt
from ecdsa import SigningKey, SECP256k1, VerifyingKey

def get_timestamp() : 
    # ct stores current time
    ct = datetime.datetime.now()
    # ts store timestamp of current time
    ts = ct.timestamp()
    return ts

def xor_sha_strings(s, t):
    # Pad the shorter string with a leading zero if its length is odd
    if len(s) % 2 == 1:
        s = '0' + s
    if len(t) % 2 == 1:
        t = '0' + t

    s_bytes = bytes.fromhex(s)
    t_bytes = bytes.fromhex(t)

    res_bytes = bytes(a ^ b for a, b in zip(s_bytes, t_bytes))
    return res_bytes.hex()

def listToString(s):
 
    # initialize an empty string
    str1 = ""
 
    # traverse in the string
    for ele in s:
        str1 += str(ele)
        str1 += ","
    str1 = str1[:len(str1)-1]
    # return string
    return str1

def inverse_mod(k, p):
    """Returns the inverse of k modulo p.

    This function returns the only integer x such that (x * k) % p == 1.

    k must be non-zero and p must be a prime.
    """
    if k == 0:
        raise ZeroDivisionError('division by zero')

    if k < 0:
        # k ** -1 = p - (-k) ** -1  (mod p)
        return p - inverse_mod(-k, p)

    # Extended Euclidean algorithm.
    s, old_s = 0, 1
    t, old_t = 1, 0
    r, old_r = p, k

    while r != 0:
        quotient = old_r // r
        old_r, r = r, old_r - quotient * r
        old_s, s = s, old_s - quotient * s
        old_t, t = t, old_t - quotient * t

    gcd, x, y = old_r, old_s, old_t

    assert gcd == 1
    assert (k * x) % p == 1

    return x % p

# Functions that work on curve points #########################################

def is_on_curve(point):
    """Returns True if the given point lies on the elliptic curve."""
    if point is None:
        # None represents the point at infinity.
        return True

    x, y = point

    return (y * y - x * x * x - curve.a * x - curve.b) % curve.p == 0


def point_neg(point):
    """Returns -point."""
    assert is_on_curve(point)

    if point is None:
        # -0 = 0
        return None

    x, y = point
    result = (x, -y % curve.p)

    assert is_on_curve(result)

    return result


def point_add(point1, point2):
    """Returns the result of point1 + point2 according to the group law."""
    assert is_on_curve(point1)
    assert is_on_curve(point2)

    if point1 is None:
        # 0 + point2 = point2
        return point2
    if point2 is None:
        # point1 + 0 = point1
        return point1

    x1, y1 = point1
    x2, y2 = point2

    if x1 == x2 and y1 != y2:
        # point1 + (-point1) = 0
        return None

    if x1 == x2:
        # This is the case point1 == point2.
        m = (3 * x1 * x1 + curve.a) * inverse_mod(2 * y1, curve.p)
    else:
        # This is the case point1 != point2.
        m = (y1 - y2) * inverse_mod(x1 - x2, curve.p)

    x3 = m * m - x1 - x2
    y3 = y1 + m * (x3 - x1)
    result = (x3 % curve.p,
              -y3 % curve.p)

    assert is_on_curve(result)

    return result


def scalar_mult(k, point):
    """Returns k * point computed using the double and point_add algorithm."""
    assert is_on_curve(point)

    if k % curve.n == 0 or point is None:
        return None

    if k < 0:
        # k * point = -k * (-point)
        return scalar_mult(-k, point_neg(point))

    result = None
    addend = point

    while k:
        if k & 1:
            # Add.
            result = point_add(result, addend)

        # Double.
        addend = point_add(addend, addend)

        k >>= 1

    assert is_on_curve(result)

    return result

# Keypair generation and ECDHE ################################################

def make_keypair():
    """Generates a random private-public key pair."""
    private_key = random.randrange(1, curve.n)
    public_key = scalar_mult(private_key, curve.g)

    return private_key, public_key

def convertTuple_str(tup):
        # initialize an empty string
    dh_str = ''
    for item in tup:
        dh_str = dh_str + str(item) + ","
    return dh_str


def handle_client(client_socket):
    print ("Veh connected \n")

    reg_flag = 0
    reg_sheet1 = pe.get_sheet (file_name= "Provable_Reg_TA_details.xlsx")
    VID_PK_VaI = client_socket.recv(1024).decode() # Recv ( VID, VPID, TPW, UID, T1) from Veh
    start1_comp_time = time.time ()

    VID_PK_VaI = [str(i) for i in VID_PK_VaI.split('&')]

    VID = VID_PK_VaI[0]
    PK_Vi = VID_PK_VaI[1]
    VaI = VID_PK_VaI[2]

    # print ("VID : ", VID)
    # print ("PK_Vi : ", PK_Vi)
    # print ("VaI : ", VaI)
    
    for row in reg_sheet1 : # Get ( VID, PID, VPID, NVID, f(w^i), fe(w^2i), fo(w^2i), Veh_Reg_comp_time )
        if row[0] == VID :
            reg_flag = 1 
            print ("  VID : ", row[0], "already found ...")
            break

    if reg_flag == 0 :
        print ("VID check success ... ")
        r = random.randint(2, 102)
        a_SK, A_PK  = make_keypair ()

        VID_VaI_r = VID +"&"+ VaI +"&"+ str(r)
        PID = encrypt(PK_TA_enc, VID_VaI_r.encode('utf-8'))

        # print ("A_PK : ", A_PK)
        # print ("\nENc PID : ", PID, type(PID))
        # print ("\nType of SK_TA : ", SK_TA)
        # print ("\nType of a_SK : ", a_SK, type (a_SK))
        # print ("\nPK_TA : ", PK_TA, type(PK_TA))
        # print ("\nr : ", r, "===================\n")

        A_PK_str = ','.join(str(num) for num in A_PK)
        # print ("PID : ", PID, type(PID))
        # print ("\nPK_Vi : ", PK_Vi, type(PK_Vi))
        # print ("\nA_PK_str : ", A_PK_str, type(A_PK_str))
        # print ("\n===================\n")
        PID_hex = PID.hex()
        # print ("Hashed Int : ", int(sha256(PID + PK_Vi.encode('utf-8') + A_PK_str.encode('utf-8')).hexdigest(), 16) )
        bi = int(sha256(PID + PK_Vi.encode('utf-8') + A_PK_str.encode('utf-8')).hexdigest(), 16) * SK_TA + a_SK
        #bi_temp = scalar_mult (int(sha256(PID + PK_Vi.encode('utf-8') + A_PK_str.encode('utf-8')).hexdigest(), 16), SK_TA)
        #bi = point_add (bi_temp, a_SK)
        
        # print ("bi is ", bi, " and type : ", type(bi))
        PID_A_b_PK_TA_r = str(PID_hex) +"$$"+ A_PK_str +"$$"+ str(bi) +"$$"+ str(PK_TA) +"$$"+ str(r)
        # print ("\nPID_A_b_PK_TA_r : ", PID_A_b_PK_TA_r)
        end1_comp_time = time.time ()
        TA_comp_time = end1_comp_time - start1_comp_time 
        client_socket.send(PID_A_b_PK_TA_r.encode('utf')) # Send ( Auth_Req, VKpubK, T1 ) to RSU
        
        print ("Total TA Comp time : ", TA_comp_time, "\n ==============================\n")

    else :
        print ("Exiting as wrong VID sent by Veh")

    
    reg_sheet1.row += [ TA_comp_time ]
    reg_sheet1.save_as ("Provable_Reg_TA_details.xlsx")


EllipticCurve = collections.namedtuple('EllipticCurve', 'name p a b g n h')

curve = EllipticCurve(
    'secp256k1',
    # Field characteristic.
    p=0xfffffffffffffffffffffffffffffffffffffffffffffffffffffffefffffc2f,
    # Curve coefficients.
    a=0,
    b=7,
    # Base point.
    g=(0x79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798,
       0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8),
    # Subgroup order.
    n=0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141,
    # Subgroup cofactor.
    h=1,
)

'''
SK_TA, PK_TA = make_keypair ()

TA_key_obj = generate_eth_key ()
SK_TA_dec = TA_key_obj.to_hex ()
PK_TA_enc = TA_key_obj.public_key.to_hex ()
'''
SK_TA = 52900507139250294659991927923573337592595124785677123083551265952472459275299
PK_TA = (52506523913431230393416036805457983909698589858860059609212415864381991957950, 19071479616544346939693675182890645267870202405760988611448411175387051499115)

PK_TA_enc = "0x4cfba5a1ed64402a123939a7c4670d7eafb87adb4999f1b4d25364fd26d87f93a87ad84b5d3cde86df9c3da71c19eb09e3eea0e85439217ee17f2116fb6f7079"
SK_TA_dec = "0x7cf70b70d179ab8553db26aff7dd1bc5b0e3d6f97713482c03350460fe3c26d0"

print ("SK_TA : ", SK_TA)
print ("PK_TA : ", PK_TA)

print ("SK_TA_dec : ", SK_TA_dec, type(SK_TA_dec))
print ("PK_TA_enc : ", PK_TA_enc, type (PK_TA_enc))

host = "localhost" # socket.gethostname()
print("Host IP is ", host)
port = 6002  # initiate port no above 1024
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # get instance
server_socket.bind((host, port))  # bind host address and port together

server_socket.listen(40)
i =0 

while True :
    client_socket, client_address = server_socket.accept()
    i = i + 1
    client_thread = threading.Thread (target=handle_client, args= (client_socket,))
    client_thread.start()