import importlib.util
import os
import unittest
from pathlib import Path

# 直接从文件加载 exclude 模块，避免触发 __init__.py 对 mcdreforged 的导入
_SPEC = importlib.util.spec_from_file_location(
    'zb_exclude', Path(__file__).resolve().parents[1] / 'zip_backup' / 'exclude.py')
exclude = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(exclude)

SERVER_PATH = 'server'


def server_path(*parts):
    return os.path.join(SERVER_PATH, *parts)


class NormalizeExcludePatternTest(unittest.TestCase):
    def test_plain_and_slash_forms(self):
        self.assertEqual(exclude.normalize_exclude_pattern('recordings'), 'recordings')
        self.assertEqual(exclude.normalize_exclude_pattern('./recordings'), 'recordings')
        self.assertEqual(exclude.normalize_exclude_pattern('recordings/'), 'recordings')
        self.assertEqual(exclude.normalize_exclude_pattern('.\\recordings'), 'recordings')
        self.assertEqual(exclude.normalize_exclude_pattern('world\\recordings'), 'world/recordings')

    def test_empty_patterns_are_invalid(self):
        self.assertIsNone(exclude.normalize_exclude_pattern(''))
        self.assertIsNone(exclude.normalize_exclude_pattern('   '))
        self.assertIsNone(exclude.normalize_exclude_pattern('/'))
        self.assertIsNone(exclude.normalize_exclude_pattern('./'))
        self.assertIsNone(exclude.normalize_exclude_pattern('.\\'))

    def test_absolute_patterns_are_invalid(self):
        # 绝对路径无法匹配相对 server_path 的路径，必须显式拒绝而不是静默变形为名称模式
        self.assertIsNone(exclude.normalize_exclude_pattern('/etc'))
        self.assertIsNone(exclude.normalize_exclude_pattern('C:/foo'))
        self.assertIsNone(exclude.normalize_exclude_pattern('c:\\foo'))


class ShouldExcludeNamePatternTest(unittest.TestCase):
    # 不含 '/' 的模式按名称匹配任意层级
    def test_directory_name_at_any_depth(self):
        self.assertTrue(exclude.should_exclude(server_path('world', 'recordings'), SERVER_PATH, ['recordings']))
        self.assertTrue(exclude.should_exclude(server_path('world', 'a', 'b', 'recordings'), SERVER_PATH, ['recordings']))

    def test_wildcard_name(self):
        self.assertTrue(exclude.should_exclude(server_path('world', 'foo.tmp'), SERVER_PATH, ['*.tmp']))
        self.assertTrue(exclude.should_exclude(server_path('world', 'region', 'r.0.0.mca'), SERVER_PATH, ['*.mca']))

    def test_file_inside_excluded_directory(self):
        self.assertTrue(exclude.should_exclude(server_path('world', 'recordings', 'a.mcpr'), SERVER_PATH, ['recordings']))

    def test_unrelated_file_is_kept(self):
        self.assertFalse(exclude.should_exclude(server_path('world', 'level.dat'), SERVER_PATH, ['recordings']))
        self.assertFalse(exclude.should_exclude(server_path('world', 'foo.dat'), SERVER_PATH, ['*.tmp']))

    def test_leading_dot_slash_pattern_is_normalized(self):
        self.assertTrue(exclude.should_exclude(server_path('world', 'recordings'), SERVER_PATH, ['./recordings']))

    def test_matching_is_case_sensitive(self):
        # 使用 fnmatchcase，各平台行为一致
        self.assertFalse(exclude.should_exclude(server_path('world', 'Recordings'), SERVER_PATH, ['recordings']))

    def test_empty_pattern_list_excludes_nothing(self):
        self.assertFalse(exclude.should_exclude(server_path('world', 'recordings'), SERVER_PATH, []))


class ShouldExcludePathPatternTest(unittest.TestCase):
    # 含 '/' 的模式相对 server_path 匹配
    def test_directory_itself_and_children(self):
        self.assertTrue(exclude.should_exclude(server_path('world', 'recordings'), SERVER_PATH, ['world/recordings']))
        self.assertTrue(exclude.should_exclude(server_path('world', 'recordings', 'a.mcpr'), SERVER_PATH, ['world/recordings']))

    def test_prefix_boundary_is_respected(self):
        self.assertFalse(exclude.should_exclude(server_path('world', 'recordings_backup', 'a'), SERVER_PATH, ['world/recordings']))

    def test_pattern_without_world_prefix_matches_under_any_parent(self):
        self.assertTrue(exclude.should_exclude(server_path('world', 'region', 'r.0.0.mca'), SERVER_PATH, ['region/*.mca']))
        self.assertTrue(exclude.should_exclude(server_path('world', 'region', 'r.0.0.mca'), SERVER_PATH, ['world/region/*.mca']))

    def test_non_matching_extension_is_kept(self):
        self.assertFalse(exclude.should_exclude(server_path('world', 'region', 'x.png'), SERVER_PATH, ['region/*.mca']))

    def test_other_world_is_kept(self):
        self.assertFalse(exclude.should_exclude(server_path('other', 'recordings', 'a'), SERVER_PATH, ['world/recordings']))

    def test_trailing_separator_in_server_path(self):
        self.assertTrue(exclude.should_exclude(server_path('world', 'recordings'), SERVER_PATH + os.sep, ['world/recordings']))

    def test_invalid_pattern_is_ignored(self):
        # 绝对路径模式被拒绝后不应影响其他模式生效
        patterns = ['/etc', 'C:/foo', 'recordings']
        self.assertTrue(exclude.should_exclude(server_path('world', 'recordings'), SERVER_PATH, patterns))
        self.assertFalse(exclude.should_exclude(server_path('world', 'etc'), SERVER_PATH, patterns))


if __name__ == '__main__':
    unittest.main()
