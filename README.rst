.. This README is meant for consumption by humans and pypi. Pypi can render rst files so please do not use Sphinx features.
   If you want to learn more about writing documentation, please check out: http://docs.plone.org/about/documentation_styleguide.html
   This text does not appear on pypi or github. It is a comment.

=====================
visaplan.plone.groups
=====================

Extended groups management for Plone

This package contains some additional groups management pages and a simple
feature for scheduled activation and termination of group memberships,
using a few tables in a PostgreSQL database
(with currently hardcoded names).

The purpose of this package (for now) is *not* to provide new functionality
but to factor out existing functionality from an existing monolitic Zope product.
Thus, it is more likely to lose functionality during further development
(as parts of it will be forked out into their own packages,
or some functionality may even become obsolete because there are better
alternatives in standard Plone components).

The additional fields for groups are not (yet) part of this package.


Features
--------

- Group administration pages 
- A very simple bulletin board for the group members
- A simple scheduler for group memberships


Examples
--------

This add-on can be seen in action at the following sites:

- https://www.unitracc.de
- https://www.unitracc.com


Documentation
-------------

Sorry, we don't have real user documentation yet.


Installation
------------

Install visaplan.plone.groups by adding it to your buildout::

    [buildout]

    ...

    eggs =
        visaplan.plone.groups


and then running ``bin/buildout``


Contribute
----------

- Issue Tracker: https://github.com/visaplan/plone.groups/issues
- Source Code: https://github.com/visaplan/plone.groups


Support
-------

If you are having issues, please let us know;
please use the `issue tracker`_ mentioned above.


License
-------

The project is licensed under the GPLv2.

.. _`issue tracker`: https://github.com/visaplan/plone.groups/issues

.. vim: tw=79 cc=+1 sw=4 sts=4 si et
