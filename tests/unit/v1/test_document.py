# Copyright 2017 Google LLC All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import collections
import unittest

import mock


class TestDocumentReference(unittest.TestCase):
    @staticmethod
    def _get_target_class():
        from google.cloud.firestore_v1.document import DocumentReference

        return DocumentReference

    def _make_one(self, *args, **kwargs):
        klass = self._get_target_class()
        return klass(*args, **kwargs)

    def test_constructor(self):
        collection_id1 = "users"
        document_id1 = "alovelace"
        collection_id2 = "platform"
        document_id2 = "*nix"
        client = mock.MagicMock()
        client.__hash__.return_value = 1234

        document = self._make_one(
            collection_id1, document_id1, collection_id2, document_id2, client=client
        )
        self.assertIs(document._client, client)
        expected_path = "/".join(
            (collection_id1, document_id1, collection_id2, document_id2)
        )
        self.assertEqual(document.path, expected_path)

    @staticmethod
    def _make_commit_repsonse(write_results=None):
        from google.cloud.firestore_v1.types import firestore

        response = mock.create_autospec(firestore.CommitResponse)
        response.write_results = write_results or [mock.sentinel.write_result]
        response.commit_time = mock.sentinel.commit_time
        return response

    @staticmethod
    def _write_pb_for_create(document_path, document_data):
        from google.cloud.firestore_v1.types import common
        from google.cloud.firestore_v1.types import document
        from google.cloud.firestore_v1.types import write
        from google.cloud.firestore_v1 import _helpers

        return write.Write(
            update=document.Document(
                name=document_path, fields=_helpers.encode_dict(document_data)
            ),
            current_document=common.Precondition(exists=False),
        )

    def _create_helper(self, retry=None, timeout=None):
        from google.cloud.firestore_v1 import _helpers

        # Create a minimal fake GAPIC with a dummy response.
        firestore_api = mock.Mock()
        firestore_api.commit.mock_add_spec(spec=["commit"])
        firestore_api.commit.return_value = self._make_commit_repsonse()

        # Attach the fake GAPIC to a real client.
        client = _make_client("dignity")
        client._firestore_api_internal = firestore_api

        # Actually make a document and call create().
        document = self._make_one("foo", "twelve", client=client)
        document_data = {"hello": "goodbye", "count": 99}
        kwargs = _helpers.make_retry_timeout_kwargs(retry, timeout)

        write_result = document.create(document_data, **kwargs)

        # Verify the response and the mocks.
        self.assertIs(write_result, mock.sentinel.write_result)
        write_pb = self._write_pb_for_create(document._document_path, document_data)
        firestore_api.commit.assert_called_once_with(
            request={
                "database": client._database_string,
                "writes": [write_pb],
                "transaction": None,
            },
            metadata=client._rpc_metadata,
            **kwargs,
        )

    def test_create(self):
        self._create_helper()

    def test_create_w_retry_timeout(self):
        from google.api_core.retry import Retry

        retry = Retry(predicate=object())
        timeout = 123.0
        self._create_helper(retry=retry, timeout=timeout)

    def test_create_empty(self):
        # Create a minimal fake GAPIC with a dummy response.
        from google.cloud.firestore_v1.document import DocumentReference
        from google.cloud.firestore_v1.document import DocumentSnapshot

        firestore_api = mock.Mock(spec=["commit"])
        document_reference = mock.create_autospec(DocumentReference)
        snapshot = mock.create_autospec(DocumentSnapshot)
        snapshot.exists = True
        document_reference.get.return_value = snapshot
        firestore_api.commit.return_value = self._make_commit_repsonse(
            write_results=[document_reference]
        )

        # Attach the fake GAPIC to a real client.
        client = _make_client("dignity")
        client._firestore_api_internal = firestore_api
        client.get_all = mock.MagicMock()
        client.get_all.exists.return_value = True

        # Actually make a document and call create().
        document = self._make_one("foo", "twelve", client=client)
        document_data = {}
        write_result = document.create(document_data)
        self.assertTrue(write_result.get().exists)

    @staticmethod
    def _write_pb_for_set(document_path, document_data, merge):
        from google.cloud.firestore_v1.types import common
        from google.cloud.firestore_v1.types import document
        from google.cloud.firestore_v1.types import write
        from google.cloud.firestore_v1 import _helpers

        write_pbs = write.Write(
            update=document.Document(
                name=document_path, fields=_helpers.encode_dict(document_data)
            )
        )
        if merge:
            field_paths = [
                field_path
                for field_path, value in _helpers.extract_fields(
                    document_data, _helpers.FieldPath()
                )
            ]
            field_paths = [
                field_path.to_api_repr() for field_path in sorted(field_paths)
            ]
            mask = common.DocumentMask(field_paths=sorted(field_paths))
            write_pbs._pb.update_mask.CopyFrom(mask._pb)
        return write_pbs

    def _set_helper(self, merge=False, retry=None, timeout=None, **option_kwargs):
        from google.cloud.firestore_v1 import _helpers

        # Create a minimal fake GAPIC with a dummy response.
        firestore_api = mock.Mock(spec=["commit"])
        firestore_api.commit.return_value = self._make_commit_repsonse()

        # Attach the fake GAPIC to a real client.
        client = _make_client("db-dee-bee")
        client._firestore_api_internal = firestore_api

        # Actually make a document and call create().
        document = self._make_one("User", "Interface", client=client)
        document_data = {"And": 500, "Now": b"\xba\xaa\xaa \xba\xaa\xaa"}
        kwargs = _helpers.make_retry_timeout_kwargs(retry, timeout)

        write_result = document.set(document_data, merge, **kwargs)

        # Verify the response and the mocks.
        self.assertIs(write_result, mock.sentinel.write_result)
        write_pb = self._write_pb_for_set(document._document_path, document_data, merge)

        firestore_api.commit.assert_called_once_with(
            request={
                "database": client._database_string,
                "writes": [write_pb],
                "transaction": None,
            },
            metadata=client._rpc_metadata,
            **kwargs,
        )

    def test_set(self):
        self._set_helper()

    def test_set_w_retry_timeout(self):
        from google.api_core.retry import Retry

        retry = Retry(predicate=object())
        timeout = 123.0
        self._set_helper(retry=retry, timeout=timeout)

    def test_set_merge(self):
        self._set_helper(merge=True)

    @staticmethod
    def _write_pb_for_update(document_path, update_values, field_paths):
        from google.cloud.firestore_v1.types import common
        from google.cloud.firestore_v1.types import document
        from google.cloud.firestore_v1.types import write
        from google.cloud.firestore_v1 import _helpers

        return write.Write(
            update=document.Document(
                name=document_path, fields=_helpers.encode_dict(update_values)
            ),
            update_mask=common.DocumentMask(field_paths=field_paths),
            current_document=common.Precondition(exists=True),
        )

    def _update_helper(self, retry=None, timeout=None, **option_kwargs):
        from google.cloud.firestore_v1 import _helpers
        from google.cloud.firestore_v1.transforms import DELETE_FIELD

        # Create a minimal fake GAPIC with a dummy response.
        firestore_api = mock.Mock(spec=["commit"])
        firestore_api.commit.return_value = self._make_commit_repsonse()

        # Attach the fake GAPIC to a real client.
        client = _make_client("potato-chip")
        client._firestore_api_internal = firestore_api

        # Actually make a document and call create().
        document = self._make_one("baked", "Alaska", client=client)
        # "Cheat" and use OrderedDict-s so that iteritems() is deterministic.
        field_updates = collections.OrderedDict(
            (("hello", 1), ("then.do", False), ("goodbye", DELETE_FIELD))
        )
        kwargs = _helpers.make_retry_timeout_kwargs(retry, timeout)

        if option_kwargs:
            option = client.write_option(**option_kwargs)
            write_result = document.update(field_updates, option=option, **kwargs)
        else:
            option = None
            write_result = document.update(field_updates, **kwargs)

        # Verify the response and the mocks.
        self.assertIs(write_result, mock.sentinel.write_result)
        update_values = {
            "hello": field_updates["hello"],
            "then": {"do": field_updates["then.do"]},
        }
        field_paths = list(field_updates.keys())
        write_pb = self._write_pb_for_update(
            document._document_path, update_values, sorted(field_paths)
        )
        if option is not None:
            option.modify_write(write_pb)
        firestore_api.commit.assert_called_once_with(
            request={
                "database": client._database_string,
                "writes": [write_pb],
                "transaction": None,
            },
            metadata=client._rpc_metadata,
            **kwargs,
        )

    def test_update_with_exists(self):
        with self.assertRaises(ValueError):
            self._update_helper(exists=True)

    def test_update(self):
        self._update_helper()

    def test_update_w_retry_timeout(self):
        from google.api_core.retry import Retry

        retry = Retry(predicate=object())
        timeout = 123.0
        self._update_helper(retry=retry, timeout=timeout)

    def test_update_with_precondition(self):
        from google.protobuf import timestamp_pb2

        timestamp = timestamp_pb2.Timestamp(seconds=1058655101, nanos=100022244)
        self._update_helper(last_update_time=timestamp)

    def test_empty_update(self):
        # Create a minimal fake GAPIC with a dummy response.
        firestore_api = mock.Mock(spec=["commit"])
        firestore_api.commit.return_value = self._make_commit_repsonse()

        # Attach the fake GAPIC to a real client.
        client = _make_client("potato-chip")
        client._firestore_api_internal = firestore_api

        # Actually make a document and call create().
        document = self._make_one("baked", "Alaska", client=client)
        # "Cheat" and use OrderedDict-s so that iteritems() is deterministic.
        field_updates = {}
        with self.assertRaises(ValueError):
            document.update(field_updates)

    def _delete_helper(self, retry=None, timeout=None, **option_kwargs):
        from google.cloud.firestore_v1 import _helpers
        from google.cloud.firestore_v1.types import write

        # Create a minimal fake GAPIC with a dummy response.
        firestore_api = mock.Mock(spec=["commit"])
        firestore_api.commit.return_value = self._make_commit_repsonse()

        # Attach the fake GAPIC to a real client.
        client = _make_client("donut-base")
        client._firestore_api_internal = firestore_api
        kwargs = _helpers.make_retry_timeout_kwargs(retry, timeout)

        # Actually make a document and call delete().
        document = self._make_one("where", "we-are", client=client)
        if option_kwargs:
            option = client.write_option(**option_kwargs)
            delete_time = document.delete(option=option, **kwargs)
        else:
            option = None
            delete_time = document.delete(**kwargs)

        # Verify the response and the mocks.
        self.assertIs(delete_time, mock.sentinel.commit_time)
        write_pb = write.Write(delete=document._document_path)
        if option is not None:
            option.modify_write(write_pb)
        firestore_api.commit.assert_called_once_with(
            request={
                "database": client._database_string,
                "writes": [write_pb],
                "transaction": None,
            },
            metadata=client._rpc_metadata,
            **kwargs,
        )

    def test_delete(self):
        self._delete_helper()

    def test_delete_with_option(self):
        from google.protobuf import timestamp_pb2

        timestamp_pb = timestamp_pb2.Timestamp(seconds=1058655101, nanos=100022244)
        self._delete_helper(last_update_time=timestamp_pb)

    def test_delete_w_retry_timeout(self):
        from google.api_core.retry import Retry

        retry = Retry(predicate=object())
        timeout = 123.0
        self._delete_helper(retry=retry, timeout=timeout)

    def _get_helper(
        self,
        field_paths=None,
        use_transaction=False,
        not_found=False,
        retry=None,
        timeout=None,
    ):
        from google.api_core.exceptions import NotFound
        from google.cloud.firestore_v1 import _helpers
        from google.cloud.firestore_v1.types import common
        from google.cloud.firestore_v1.types import document
        from google.cloud.firestore_v1.transaction import Transaction

        # Create a minimal fake GAPIC with a dummy response.
        create_time = 123
        update_time = 234
        firestore_api = mock.Mock(spec=["get_document"])
        response = mock.create_autospec(document.Document)
        response.fields = {}
        response.create_time = create_time
        response.update_time = update_time

        if not_found:
            firestore_api.get_document.side_effect = NotFound("testing")
        else:
            firestore_api.get_document.return_value = response

        client = _make_client("donut-base")
        client._firestore_api_internal = firestore_api

        document = self._make_one("where", "we-are", client=client)

        if use_transaction:
            transaction = Transaction(client)
            transaction_id = transaction._id = b"asking-me-2"
        else:
            transaction = None

        kwargs = _helpers.make_retry_timeout_kwargs(retry, timeout)

        snapshot = document.get(
            field_paths=field_paths, transaction=transaction, **kwargs
        )

        self.assertIs(snapshot.reference, document)
        if not_found:
            self.assertIsNone(snapshot._data)
            self.assertFalse(snapshot.exists)
            self.assertIsNone(snapshot.read_time)
            self.assertIsNone(snapshot.create_time)
            self.assertIsNone(snapshot.update_time)
        else:
            self.assertEqual(snapshot.to_dict(), {})
            self.assertTrue(snapshot.exists)
            self.assertIsNone(snapshot.read_time)
            self.assertIs(snapshot.create_time, create_time)
            self.assertIs(snapshot.update_time, update_time)

        # Verify the request made to the API
        if field_paths is not None:
            mask = common.DocumentMask(field_paths=sorted(field_paths))
        else:
            mask = None

        if use_transaction:
            expected_transaction_id = transaction_id
        else:
            expected_transaction_id = None

        firestore_api.get_document.assert_called_once_with(
            request={
                "name": document._document_path,
                "mask": mask,
                "transaction": expected_transaction_id,
            },
            metadata=client._rpc_metadata,
            **kwargs,
        )

    def test_get_not_found(self):
        self._get_helper(not_found=True)

    def test_get_default(self):
        self._get_helper()

    def test_get_w_retry_timeout(self):
        from google.api_core.retry import Retry

        retry = Retry(predicate=object())
        timeout = 123.0
        self._get_helper(retry=retry, timeout=timeout)

    def test_get_w_string_field_path(self):
        with self.assertRaises(ValueError):
            self._get_helper(field_paths="foo")

    def test_get_with_field_path(self):
        self._get_helper(field_paths=["foo"])

    def test_get_with_multiple_field_paths(self):
        self._get_helper(field_paths=["foo", "bar.baz"])

    def test_get_with_transaction(self):
        self._get_helper(use_transaction=True)

    def _collections_helper(self, page_size=None, retry=None, timeout=None):
        from google.cloud.firestore_v1.collection import CollectionReference
        from google.cloud.firestore_v1 import _helpers
        from google.cloud.firestore_v1.services.firestore.client import FirestoreClient

        collection_ids = ["coll-1", "coll-2"]

        class Pager(object):
            def __iter__(self):
                yield from collection_ids

        api_client = mock.create_autospec(FirestoreClient)
        api_client.list_collection_ids.return_value = Pager()

        client = _make_client()
        client._firestore_api_internal = api_client
        kwargs = _helpers.make_retry_timeout_kwargs(retry, timeout)

        # Actually make a document and call delete().
        document = self._make_one("where", "we-are", client=client)
        if page_size is not None:
            collections = list(document.collections(page_size=page_size, **kwargs))
        else:
            collections = list(document.collections(**kwargs))

        # Verify the response and the mocks.
        self.assertEqual(len(collections), len(collection_ids))
        for collection, collection_id in zip(collections, collection_ids):
            self.assertIsInstance(collection, CollectionReference)
            self.assertEqual(collection.parent, document)
            self.assertEqual(collection.id, collection_id)

        api_client.list_collection_ids.assert_called_once_with(
            request={"parent": document._document_path, "page_size": page_size},
            metadata=client._rpc_metadata,
            **kwargs,
        )

    def test_collections_wo_page_size(self):
        self._collections_helper()

    def test_collections_w_page_size(self):
        self._collections_helper(page_size=10)

    def test_collections_w_retry_timeout(self):
        from google.api_core.retry import Retry

        retry = Retry(predicate=object())
        timeout = 123.0
        self._collections_helper(retry=retry, timeout=timeout)

    @mock.patch("google.cloud.firestore_v1.document.Watch", autospec=True)
    def test_on_snapshot(self, watch):
        client = mock.Mock(_database_string="sprinklez", spec=["_database_string"])
        document = self._make_one("yellow", "mellow", client=client)
        document.on_snapshot(None)
        watch.for_document.assert_called_once()


def _make_credentials():
    import google.auth.credentials

    return mock.Mock(spec=google.auth.credentials.Credentials)


def _make_client(project="project-project"):
    from google.cloud.firestore_v1.client import Client

    credentials = _make_credentials()
    return Client(project=project, credentials=credentials)
