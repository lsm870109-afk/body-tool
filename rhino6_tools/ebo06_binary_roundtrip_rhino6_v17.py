# -*- coding: utf-8 -*-
# NBA Live 06 EBO Binary Load / Save Round-trip
# Rhino 6 / IronPython 2.7
# V17 - binary preservation baseline
#
# This script does NOT decode or modify geometry.
# It loads an EBO as raw bytes, saves a copy, then verifies byte identity.

import os
import struct
import Rhino
import scriptcontext as sc
from System.Windows.Forms import OpenFileDialog, SaveFileDialog, DialogResult
from System.IO import File
from System.Security.Cryptography import SHA256
from System import BitConverter


def sha256_bytes(data):
    sha = SHA256.Create()
    try:
        digest = sha.ComputeHash(data)
        return BitConverter.ToString(digest).Replace("-", "").ToLower()
    finally:
        sha.Dispose()


def read_ebo(path):
    data = File.ReadAllBytes(path)

    if len(data) < 12:
        raise Exception("File is too small to be a valid EBO.")

    if data[0] != 0x45 or data[1] != 0x42 or data[2] != 0x4F or data[3] != 0x00:
        raise Exception("Invalid EBO magic. Expected EBO\\x00.")

    version = BitConverter.ToUInt32(data, 4)
    declared_size = BitConverter.ToUInt32(data, 8)

    return data, version, declared_size


def arrays_equal(a, b):
    if len(a) != len(b):
        return False
    for i in range(len(a)):
        if a[i] != b[i]:
            return False
    return True


def main():
    open_dlg = OpenFileDialog()
    open_dlg.Title = "Select NBA Live 06 EBO file"
    open_dlg.Filter = "EBO files (*.ebo)|*.ebo|All files (*.*)|*.*"
    open_dlg.Multiselect = False

    if open_dlg.ShowDialog() != DialogResult.OK:
        print("Cancelled: no input file selected.")
        return

    source_path = open_dlg.FileName
    data, version, declared_size = read_ebo(source_path)

    print("")
    print("=" * 68)
    print("EBO LOAD SUCCESS")
    print("SOURCE       : %s" % source_path)
    print("ACTUAL SIZE  : %d bytes" % len(data))
    print("EBO VERSION  : %d" % version)
    print("HEADER SIZE  : %d bytes" % declared_size)
    print("HEADER MATCH : %s" % ("YES" if declared_size == len(data) else "NO - investigate header interpretation"))
    print("SHA256       : %s" % sha256_bytes(data))
    print("SOURCE EDITED: NO")
    print("=" * 68)

    save_dlg = SaveFileDialog()
    save_dlg.Title = "Save an unchanged EBO copy"
    save_dlg.Filter = "EBO files (*.ebo)|*.ebo|All files (*.*)|*.*"
    save_dlg.FileName = os.path.splitext(os.path.basename(source_path))[0] + "_roundtrip.ebo"
    save_dlg.OverwritePrompt = True

    if save_dlg.ShowDialog() != DialogResult.OK:
        print("Cancelled: source was loaded but no copy was saved.")
        return

    output_path = save_dlg.FileName

    if os.path.abspath(source_path).lower() == os.path.abspath(output_path).lower():
        raise Exception("Choose a different output path. The original file must not be overwritten.")

    File.WriteAllBytes(output_path, data)

    saved = File.ReadAllBytes(output_path)
    same = arrays_equal(data, saved)
    source_hash = sha256_bytes(data)
    saved_hash = sha256_bytes(saved)

    print("")
    print("=" * 68)
    print("EBO SAVE / ROUND-TRIP RESULT")
    print("OUTPUT       : %s" % output_path)
    print("SAVED SIZE   : %d bytes" % len(saved))
    print("SOURCE SHA256: %s" % source_hash)
    print("SAVED SHA256 : %s" % saved_hash)
    print("BYTE IDENTICAL: %s" % ("PASS" if same and source_hash == saved_hash else "FAIL"))
    print("ORIGINAL FILE : UNCHANGED")
    print("=" * 68)

    if same and source_hash == saved_hash:
        print("V17 PASS: EBO raw binary load/save round-trip verified.")
    else:
        print("V17 FAIL: saved file differs from source. Do not use this copy.")


if __name__ == "__main__":
    main()
