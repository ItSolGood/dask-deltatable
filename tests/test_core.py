import zipfile
from io import BytesIO

import pytest

import dask_deltatable as ddt

requests = pytest.importorskip("requests")


@pytest.fixture()
def simple_table(tmpdir):
    output_dir = tmpdir
    deltaf = zipfile.ZipFile("tests/data/simple.zip")
    deltaf.extractall(output_dir)
    return output_dir + "/test1/"


@pytest.fixture()
def partition_table(tmpdir):
    output_dir = tmpdir
    deltaf = zipfile.ZipFile("tests/data/partition.zip")
    deltaf.extractall(output_dir)
    return output_dir + "/test2/"


@pytest.fixture()
def empty_table1(tmpdir):
    output_dir = tmpdir
    deltaf = zipfile.ZipFile("tests/data/empty1.zip")
    deltaf.extractall(output_dir)
    return output_dir + "/empty/"


@pytest.fixture()
def empty_table2(tmpdir):
    output_dir = tmpdir
    deltaf = zipfile.ZipFile("tests/data/empty2.zip")
    deltaf.extractall(output_dir)
    return output_dir + "/empty2/"


@pytest.fixture()
def checkpoint_table(tmpdir):
    output_dir = tmpdir
    deltaf = zipfile.ZipFile("tests/data/checkpoint.zip")
    deltaf.extractall(output_dir)
    return output_dir + "/checkpoint/"


def test_read_delta(simple_table):
    df = ddt.read_delta_table(simple_table)

    assert df.columns.tolist() == ["id", "count", "temperature", "newColumn"]
    assert df.compute().shape == (200, 4)


def test_read_delta_with_different_versions(simple_table):
    df = ddt.read_delta_table(simple_table, version=0)
    assert df.compute().shape == (100, 3)

    df = ddt.read_delta_table(simple_table, version=1)
    assert df.compute().shape == (200, 4)


def test_row_filter(simple_table):
    # row filter
    df = ddt.read_delta_table(simple_table, version=0, filter=[("count", ">", 30)],)
    assert df.compute().shape == (61, 3)


def test_different_columns(simple_table):
    df = ddt.read_delta_table(simple_table, columns=["count", "temperature"])
    assert df.columns.tolist() == ["count", "temperature"]


def test_different_schema(simple_table):
    # testing schema evolution

    df = ddt.read_delta_table(simple_table, version=0)
    assert df.columns.tolist() == ["id", "count", "temperature"]

    df = ddt.read_delta_table(simple_table, version=1)
    assert df.columns.tolist() == ["id", "count", "temperature", "newColumn"]


def test_partition_filter(partition_table):
    # partition filter
    df = ddt.read_delta_table(partition_table, version=0, filter=[("col1", "==", 1)])
    assert df.compute().shape == (21, 3)

    df = ddt.read_delta_table(
        partition_table, filter=[[("col1", "==", 1)], [("col1", "==", 2)]]
    )
    assert df.compute().shape == (39, 4)


def test_empty(empty_table1, empty_table2):
    df = ddt.read_delta_table(empty_table1, version=4)
    assert df.compute().shape == (0, 2)

    df = ddt.read_delta_table(empty_table1, version=0)
    assert df.compute().shape == (5, 2)

    with pytest.raises(RuntimeError):
        # No Parquet files found
        _ = ddt.read_delta_table(empty_table2)


def test_checkpoint(checkpoint_table):
    df = ddt.read_delta_table(checkpoint_table, checkpoint=0, version=4)
    assert df.compute().shape[0] == 25

    df = ddt.read_delta_table(checkpoint_table, checkpoint=10, version=12)
    assert df.compute().shape[0] == 65

    df = ddt.read_delta_table(checkpoint_table, checkpoint=20, version=22)
    assert df.compute().shape[0] == 115

    with pytest.raises(ValueError):
        # Parquet file with the given checkpoint 30 does not exists:
        # File {checkpoint_path} not found"
        _ = ddt.read_delta_table(checkpoint_table, checkpoint=30, version=33)


def test_out_of_version_error(simple_table):
    # Cannot time travel Delta table to version 4 , Available versions for given
    # checkpoint 0 are [0,1]
    with pytest.raises(ValueError):
        _ = ddt.read_delta_table(simple_table, version=4)
