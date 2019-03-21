import pytest

from libcloud.storage.drivers.dummy import DummyStorageDriver


@pytest.fixture
def driver():
    return DummyStorageDriver('key', 'id')


@pytest.fixture
def container_with_contents(driver):
    container_name = 'test'
    object_name = 'test.dat'
    container = driver.create_container(container_name=container_name)
    driver.upload_object(
        __file__, container=container, object_name=object_name
    )
    return container_name, object_name


def test_list_container_objects(driver, container_with_contents):
    container_name, object_name = container_with_contents
    container = driver.get_container(container_name)

    objects = driver.list_container_objects(container=container)

    assert any(o for o in objects if o.name == object_name)


def test_list_container_objects_filter_by_prefix(
    driver, container_with_contents
):
    container_name, object_name = container_with_contents
    container = driver.get_container(container_name)

    objects = driver.list_container_objects(
        container=container, ex_prefix=object_name[:3]
    )
    assert any(o for o in objects if o.name == object_name)

    objects = driver.list_container_objects(
        container=container, ex_prefix='does-not-exist.dat'
    )
    assert not objects
