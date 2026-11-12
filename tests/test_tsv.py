import csv
import io
import sys

import pytest
from click.testing import CliRunner

from deepdiff.commands import diff, patch
from deepdiff.serialization import load_path_content, save_content_to_path


@pytest.mark.parametrize('file_type,delimiter', [('csv', ','), ('tsv', '\t')])
@pytest.mark.parametrize('use_clevercsv', [False, True])
def test_delimited_file_round_trip(tmp_path, monkeypatch, file_type, delimiter, use_clevercsv):
    if use_clevercsv:
        pytest.importorskip('clevercsv')
    else:
        monkeypatch.setitem(sys.modules, 'clevercsv', None)
    before = [{'name': 'Alice, "A"', 'note': 'line one\nline two', 'value': 1}]
    after = [{'name': 'Alice, "A"', 'note': 'left\tright', 'value': 2}]
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=['name', 'note', 'value'], delimiter=delimiter)
    writer.writeheader()
    writer.writerows(before)
    path = tmp_path / f'data.{file_type}'
    original = buffer.getvalue().encode()
    path.write_bytes(original)

    assert load_path_content(str(path)) == before
    save_content_to_path(after, str(path), file_type=file_type)

    with path.open(newline='') as stream:
        rows = list(csv.DictReader(stream, delimiter=delimiter))
    assert rows == [{**after[0], 'value': '2'}]
    assert path.with_suffix(f'.{file_type}.bak').read_bytes() == original
    assert load_path_content(str(path)) == after


@pytest.mark.parametrize('use_clevercsv', [False, True])
def test_tsv_patch_preserves_tab_delimiters(tmp_path, monkeypatch, use_clevercsv):
    if use_clevercsv:
        pytest.importorskip('clevercsv')
    else:
        monkeypatch.setitem(sys.modules, 'clevercsv', None)
    source = tmp_path / 'source.tsv'
    target = tmp_path / 'target.tsv'
    delta = tmp_path / 'delta.pickle'
    original = b'name\tvalue\nAlice\t1\n'
    source.write_bytes(original)
    target.write_bytes(b'name\tvalue\nAlice\t2\n')
    assert load_path_content(str(source)) == [{'name': 'Alice', 'value': 1}]
    runner = CliRunner()
    generated = runner.invoke(diff, [str(source), str(target), '--create-patch'])
    assert generated.exit_code == 0, generated.output
    delta.write_bytes(generated.stdout_bytes)

    applied = runner.invoke(patch, [str(source), str(delta), '--backup'])
    assert applied.exit_code == 0, applied.output
    with source.open(newline='') as stream:
        assert list(csv.DictReader(stream, delimiter='\t')) == [{'name': 'Alice', 'value': '2'}]
    assert source.with_suffix('.tsv.bak').read_bytes() == original
