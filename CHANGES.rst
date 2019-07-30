Changelog
=========


1.0.1 (2019-05-09)
------------------

- New functions ``utils.generate_{structure,course}_group_ids``,
  ``generate_structure_group_tuples``

- Support for option ``resolve_role`` for the following functions:

  - ``split_group_id``
  - ``generate_structure_group_tuples``

  With ``resolve_role=True``, these functions tell a role a role, and a
  suffix a suffix; e.g., the ``Author`` group of structures is not given the
  ``Author`` but the ``Editor`` local role.

  For now, the default value for ``resolve_role`` is *False*;
  this may change in future versions.

[tobiasherp]


1.0 (2018-09-19)
----------------

- Initial release.
  [tobiasherp]
