"""Tests for util.naming"""
from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 3.0 or later"

# TODO: Decide on a name for the program and rename "src"
from src.util.naming import filename_to_name, PROGRAM_EXTS

# TODO: unittest.TestCase for titlecase_up()

# Minimal set of extensions one might expect a game to use
# (For whitelist-based extension stripping so it's not too greedy)
test_program_exts = (
    '.air', '.swf', '.jar',
    '.sh', '.py', '.pl',
    '.exe', '.bat', '.cmd', '.pif',
    '.bin',
    '.desktop',
)

filename_test_map = {
    'Aaaaa_Awesome_x64_Linux': ['Aaaaa Awesome'],
    'AndroVMplayer-Linux64': ['AndroVMplayer'],
    'Anodyne_STANDALONE_1_506.swf': ['Anodyne'],
    'Antichamber': ['Antichamber'],
    'avadon': ['Avadon'],
    'beatblastersiii': ['Beatblasters III', 'BeatblastersIII',
                        'Beat Blasters III'],
    'Beatbuddy': ['Beatbuddy', 'Beat Buddy'],
    'BravadaLinux': ['Bravada'],
    'capsized': ['Capsized'],
    'CaveStory+': ['Cave Story+'],
    'ColorOracle.jar': ['Color Oracle'],
    'dearesther': ['Dear Esther', 'Dearesther'],
    'DesktopDungeons': ['Desktop Dungeons'],
    'djgpp': ['DJGPP', 'Djgpp'],
    'dolphin-emu': ['Dolphin Emu'],
    'doom-and-destiny': ['Doom And Destiny'],
    'eets2': ['Eets 2'],
    'elliot_quest': ['Elliot Quest'],
    'epubcheck-3.0.1': ['Epubcheck'],
    'escapegoat2': ['Escape Goat 2', 'Escapegoat 2'],
    'etherpad-lite': ['Etherpad Lite', 'Ether Pad Lite'],
    'Eufloria': ['Eufloria'],
    'fennec-4.0.1': ['Fennec'],
    'fennec-7.0.1': ['Fennec'],
    'firefox': ['Firefox'],
    'firefox-ux': ['Firefox UX'],
    'firefox_4.0': ['Firefox'],
    'firefox_stable': ['Firefox Stable'],
    'fortune': ['Fortune'],
    'FTL': ['FTL'],
    'grimrock': ['Grimrock'],
    'GSB': ['GSB'],
    'Guacamelee': ['Guacamelee'],
    'Gunpoint': ['Gunpoint'],
    'hobl_linux64': ['HOBL', 'Hobl'],
    'INVedit': ['INVedit'],
    'IttleDewLinux': ['Ittle Dew'],
    'jamestown': ['Jamestown', 'James Town'],
    'jarnal': ['Jarnal'],
    'kagbeta-linux32-client': ['KAG Client', 'Kag Client'],
    'Knytt Underground': ['Knytt Underground'],
    'LanguageTool': ['LanguageTool', 'Language Tool'],
    'MarkOfTheNinja': ['Mark Of The Ninja'],
    'McPixel': ['McPixel'],
    'minecraft.jar': ['Minecraft'],
    'minecraft_server': ['Minecraft Server'],
    'NBTExplorer': ['NBT Explorer'],
    'nihilumbra': ['Nihilumbra'],
    'Noire 1.01.swf': ['Noire'],
    'Not the Robots_Linux': ['Not The Robots'],
    'pandora-dev': ['Pandora Dev'],
    'poclbm': ['Poclbm'],
    'Potatoman': ['Potatoman'],
    'prisonarchitect-alpha24c-linux': ['Prison Architect', 'Prisonarchitect'],
    'processing-1.5.1': ['Processing'],
    'RaceTheSun_1.10_LINUX': ['Race The Sun'],
    'railyard': ['Railyard', 'Rail Yard'],
    'reus': ['Reus'],
    'roguelegacy': ['Rogue Legacy', 'Roguelegacy'],
    'RogueLegacyLinux_v120a': ['Rogue Legacy'],
    'runic-temp': ['Runic Temp'],
    'shipwreck': ['Shipwreck'],
    'Solar2': ['Solar 2'],
    'Soundfonts': ['Soundfonts', 'Sound Fonts'],
    'spaz': ['SPAZ', 'Spaz'],
    'supermeatboy': ['Super Meat Boy', 'Supermeatboy'],
    'teensyduino': ['Teensyduino'],
    'The Bard\'s Tale': ['The Bard\'s Tale'],
    'The Basement Collection': ['The Basement Collection'],
    'TestyMacJohnson': ['Testy MacJohnson'],
    'Testy-MacJohnson': ['Testy MacJohnson'],
    'Testy_MacJohnson': ['Testy MacJohnson'],
    'testilizationI': ['Testilization I'],
    'testilizationII': ['Testilization II'],
    'testilizationIII': ['Testilization III'],
    'testilizationIV': ['Testilization IV'],
    'testilizationV': ['Testilization V'],
    'testilizationVI': ['Testilization VI'],
    'time-swap': ['Time Swap'],
    'torchlight': ['Torchlight', 'Torch Light'],
    'ToTheMoon': ['To The Moon'],
    'trine2_linux': ['Trine 2'],
    'trine2_complete_story_v2_01_build_425_humble_linux': ['Trine2 Complete Story', 'Trine 2 Complete Story'],
    'Ultionus': ['Ultionus'],
    'unxwb': ['UnXWB'],
    'uplink-x64': ['Uplink'],
    'vessel': ['Vessel'],
    'x-com db 1.4': ['X-Com DB'],
}
filename_test_map.update({'test' + x: ['Test'] for x in test_program_exts})

def test_program_ext_completeness():
    """Test for comprehensiveness of PROGRAM_EXTS-stripping test"""
    missed = [x for x in test_program_exts if x not in PROGRAM_EXTS]
    assert not missed, "Extensions not in PROGRAM_EXTS: %s" % missed

    excess = [x for x in PROGRAM_EXTS if x not in test_program_exts]
    assert not excess, "Extensions in PROGRAM_EXTS but not test: %s" % excess

def test_filename_to_name():
    """Test for sufficient accuracy of guesses by filename_to_name()"""
    score = 0
    failures = {}

    for key, valid_results in filename_test_map.items():
        this_score, result = -10, filename_to_name(key)
        for pos, val in enumerate(valid_results):
            if result == val:
                this_score = -pos
                break

        score += this_score
        if this_score < 0:
            failures[key] = (key, result, valid_results[0])

    fail_count, total_count = len(failures), len(filename_test_map)
    message = "\nFailed to perfectly guess %s of %s titles (%.2f%%):\n" % (
                fail_count, total_count, (fail_count / total_count * 100))
    for val in failures.values():
        message += "\t%-35s-> %-35s (not %s)\n" % val
    message += "Final accuracy score: %s" % score
    print(message)

    assert score > -10

