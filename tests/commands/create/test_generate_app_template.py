import os
import platform
import subprocess
from datetime import date
from pathlib import Path
from unittest import mock

import pytest
from cookiecutter import exceptions as cookiecutter_exceptions
from git import exc as git_exceptions

import briefcase
from briefcase.commands.base import (
    InvalidTemplateRepository,
    TemplateUnsupportedVersion,
)
from briefcase.exceptions import NetworkFailure


@pytest.fixture
def full_context():
    return {
        "app_name": "my-app",
        "formal_name": "My App",
        "bundle": "com.example",
        "version": "1.2.3",
        "description": "This is a simple app",
        "sources": ["src/my_app"],
        "url": "https://example.com",
        "author": "First Last",
        "author_email": "first@example.com",
        "requires": None,
        "icon": None,
        "splash": None,
        "supported": True,
        "document_types": {},
        # Properties of the generating environment
        "python_version": platform.python_version(),
        # Fields generated from other properties
        "module_name": "my_app",
        "package_name": "com.example",
        # Date-based fields added at time of generation
        "year": date.today().strftime("%Y"),
        "month": date.today().strftime("%B"),
        # Fields added by the output format.
        "output_format": "dummy",
    }


@pytest.mark.parametrize(
    "briefcase_version",
    [
        "37.42.7",
        "37.42.7.dev73+gad61a29.d20220919",
        "37.42.7a1",
        "37.42.7b2",
        "37.42.7rc3",
        "37.42.7.post1",
    ],
)
def test_default_template(
    monkeypatch, create_command, myapp, full_context, briefcase_version
):
    """Absent of other information, the briefcase version (without suffixes) is
    used as the template branch."""
    # Set the Briefcase version
    monkeypatch.setattr(briefcase, "__version__", briefcase_version)

    # There won't be a cookiecutter cache, so there won't be
    # a cache path (yet).
    create_command.git.Repo.side_effect = git_exceptions.NoSuchPathError

    # Generate the template.
    create_command.generate_app_template(myapp)

    # App's template has been set
    assert (
        myapp.template
        == "https://github.com/beeware/briefcase-tester-dummy-template.git"
    )

    # Cookiecutter was invoked with the expected template name and context.
    create_command.cookiecutter.assert_called_once_with(
        "https://github.com/beeware/briefcase-tester-dummy-template.git",
        no_input=True,
        checkout="v37.42.7",
        output_dir=os.fsdecode(create_command.platform_path),
        extra_context=full_context,
    )


def test_default_template_dev(monkeypatch, create_command, myapp, full_context):
    """In a dev version, template will fall back to the 'main' branch if a
    versioned template doesn't exist."""
    # Set the Briefcase version
    monkeypatch.setattr(briefcase, "__version__", "37.42.7.dev73+gad61a29.d20220919")

    # There won't be a cookiecutter cache, so there won't be
    # a cache path (yet).
    create_command.git.Repo.side_effect = git_exceptions.NoSuchPathError

    # There will be two calls to cookiecutter; one on the versioned branch,
    # and one on the `main` branch. The first call will fail because the
    # template doesn't exist yet; the second will succeed.
    create_command.cookiecutter.side_effect = [
        cookiecutter_exceptions.RepositoryCloneFailed,
        None,
    ]

    # Generate the template.
    create_command.generate_app_template(myapp)

    # App's template has been set
    assert (
        myapp.template
        == "https://github.com/beeware/briefcase-tester-dummy-template.git"
    )

    # Cookiecutter was invoked with the expected template name and context.
    create_command.cookiecutter.assert_has_calls(
        [
            mock.call(
                "https://github.com/beeware/briefcase-tester-dummy-template.git",
                no_input=True,
                checkout="v37.42.7",
                output_dir=os.fsdecode(create_command.platform_path),
                extra_context=full_context,
            ),
            mock.call(
                "https://github.com/beeware/briefcase-tester-dummy-template.git",
                no_input=True,
                checkout="main",
                output_dir=os.fsdecode(create_command.platform_path),
                extra_context=full_context,
            ),
        ]
    )


def test_explicit_branch(monkeypatch, create_command, myapp, full_context):
    """user can choose which branch to take the template from."""
    # Set the Briefcase version
    monkeypatch.setattr(briefcase, "__version__", "37.42.7")

    branch = "some_branch"
    myapp.template_branch = branch
    create_command.git.Repo.side_effect = git_exceptions.NoSuchPathError

    # Generate the template.
    create_command.generate_app_template(myapp)

    # App's template has been set
    assert (
        myapp.template
        == "https://github.com/beeware/briefcase-tester-dummy-template.git"
    )

    # Cookiecutter was invoked with the expected template name and context.
    create_command.cookiecutter.assert_called_once_with(
        "https://github.com/beeware/briefcase-tester-dummy-template.git",
        no_input=True,
        checkout=branch,
        output_dir=os.fsdecode(create_command.platform_path),
        extra_context=full_context,
    )


def test_platform_exists(monkeypatch, create_command, myapp, full_context):
    """If the platform directory already exists, it's ok."""
    # Set the Briefcase version
    monkeypatch.setattr(briefcase, "__version__", "37.42.7")

    # There won't be a cookiecutter cache, so there won't be
    # a cache path (yet).
    create_command.git.Repo.side_effect = git_exceptions.NoSuchPathError

    # Create the platform directory
    create_command.platform_path.mkdir(parents=True)

    # Generate the template.
    create_command.generate_app_template(myapp)

    # App's template has been set
    assert (
        myapp.template
        == "https://github.com/beeware/briefcase-tester-dummy-template.git"
    )

    # Cookiecutter was invoked with the expected template name and context.
    create_command.cookiecutter.assert_called_once_with(
        "https://github.com/beeware/briefcase-tester-dummy-template.git",
        no_input=True,
        checkout="v37.42.7",
        output_dir=os.fsdecode(create_command.platform_path),
        extra_context=full_context,
    )


def test_explicit_repo_template(monkeypatch, create_command, myapp, full_context):
    """If a template is specified in the app config, it is used."""
    # Set the Briefcase version
    monkeypatch.setattr(briefcase, "__version__", "37.42.7")

    myapp.template = "https://example.com/magic/special-template.git"

    # There won't be a cookiecutter cache, so there won't be
    # a repo path (yet).
    create_command.git.Repo.side_effect = git_exceptions.NoSuchPathError

    # Generate the template.
    create_command.generate_app_template(myapp)

    # App's template hasn't been changed
    assert myapp.template == "https://example.com/magic/special-template.git"

    # Cookiecutter was invoked with the expected template name and context.
    create_command.cookiecutter.assert_called_once_with(
        "https://example.com/magic/special-template.git",
        no_input=True,
        checkout="v37.42.7",
        output_dir=os.fsdecode(create_command.platform_path),
        extra_context=full_context,
    )


def test_explicit_local_template(monkeypatch, create_command, myapp, full_context):
    """If a local template path is specified in the app config, it is used."""
    # Set the Briefcase version
    monkeypatch.setattr(briefcase, "__version__", "37.42.7")

    myapp.template = "/path/to/special-template"

    # Generate the template.
    create_command.generate_app_template(myapp)

    # App's template hasn't been changed
    assert myapp.template == "/path/to/special-template"

    # Cookiecutter was invoked with the expected template name and context.
    create_command.cookiecutter.assert_called_once_with(
        "/path/to/special-template",
        no_input=True,
        checkout="v37.42.7",
        output_dir=os.fsdecode(create_command.platform_path),
        extra_context=full_context,
    )

    # The template is a local directory, so there won't be any calls on git.
    assert create_command.git.Repo.call_count == 0


def test_offline_repo_template(monkeypatch, create_command, myapp, full_context):
    """If the user is offline the first time a repo template is requested, an
    error is raised."""
    # Set the Briefcase version
    monkeypatch.setattr(briefcase, "__version__", "37.42.7")

    # There won't be a cookiecutter cache, so there won't be
    # a repo path (yet).
    create_command.git.Repo.side_effect = git_exceptions.NoSuchPathError

    # Calling cookiecutter on a repository while offline causes a CalledProcessError
    create_command.cookiecutter.side_effect = subprocess.CalledProcessError(
        cmd=[
            "git",
            "clone",
            "https://github.com/beeware/briefcase-tester-dummy-template.git",
        ],
        returncode=128,
    )

    # Generating the template under these conditions raises an error
    with pytest.raises(NetworkFailure):
        create_command.generate_app_template(myapp)

    # App's template has been set
    assert (
        myapp.template
        == "https://github.com/beeware/briefcase-tester-dummy-template.git"
    )

    # Cookiecutter was invoked with the expected template name and context.
    create_command.cookiecutter.assert_called_once_with(
        "https://github.com/beeware/briefcase-tester-dummy-template.git",
        no_input=True,
        checkout="v37.42.7",
        output_dir=os.fsdecode(create_command.platform_path),
        extra_context=full_context,
    )


def test_invalid_repo_template(monkeypatch, create_command, myapp, full_context):
    """If the provided template URL isn't valid, an error is raised."""
    # Set the Briefcase version
    monkeypatch.setattr(briefcase, "__version__", "37.42.7")

    myapp.template = "https://example.com/somewhere/not-a-repo.git"

    # There won't be a cookiecutter cache, so there won't be
    # a repo path (yet).
    create_command.git.Repo.side_effect = git_exceptions.NoSuchPathError

    # Calling cookiecutter on a URL that isn't a valid repository causes an error
    create_command.cookiecutter.side_effect = cookiecutter_exceptions.RepositoryNotFound

    # Generating the template under there conditions raises an error
    with pytest.raises(InvalidTemplateRepository):
        create_command.generate_app_template(myapp)

    # App's template is unchanged
    assert myapp.template == "https://example.com/somewhere/not-a-repo.git"

    # Cookiecutter was invoked with the expected template name and context.
    create_command.cookiecutter.assert_called_once_with(
        "https://example.com/somewhere/not-a-repo.git",
        no_input=True,
        checkout="v37.42.7",
        output_dir=os.fsdecode(create_command.platform_path),
        extra_context=full_context,
    )


def test_missing_branch_template(monkeypatch, create_command, myapp, full_context):
    """If the repo at the provided template URL doesn't have a branch for this
    Python version, an error is raised."""
    # Set the Briefcase version
    monkeypatch.setattr(briefcase, "__version__", "37.42.7")

    myapp.template = "https://example.com/somewhere/missing-branch.git"

    # There won't be a cookiecutter cache, so there won't be
    # a repo path (yet).
    create_command.git.Repo.side_effect = git_exceptions.NoSuchPathError

    # Calling cookiecutter on a URL that doesn't have the requested branch
    # causes an error
    create_command.cookiecutter.side_effect = (
        cookiecutter_exceptions.RepositoryCloneFailed
    )

    # Generating the template under there conditions raises an error
    with pytest.raises(TemplateUnsupportedVersion):
        create_command.generate_app_template(myapp)

    # App's template is unchanged
    assert myapp.template == "https://example.com/somewhere/missing-branch.git"

    # Cookiecutter was invoked with the expected template name and context.
    create_command.cookiecutter.assert_called_once_with(
        "https://example.com/somewhere/missing-branch.git",
        no_input=True,
        checkout="v37.42.7",
        output_dir=os.fsdecode(create_command.platform_path),
        extra_context=full_context,
    )


def test_cached_template(monkeypatch, create_command, myapp, full_context):
    """If a template has already been used, the cached version will be used."""
    # Set the Briefcase version
    monkeypatch.setattr(briefcase, "__version__", "37.42.7")

    mock_repo = mock.MagicMock()
    mock_remote = mock.MagicMock()
    mock_remote_head = mock.MagicMock()

    # Git returns a Repo, that repo can return a remote, and it has
    # heads that can be accessed.
    create_command.git.Repo.return_value = mock_repo
    mock_repo.remote.return_value = mock_remote
    mock_remote.refs.__getitem__.return_value = mock_remote_head

    # Generate the template.
    create_command.generate_app_template(myapp)

    # The origin of the repo was fetched
    mock_repo.remote.assert_called_once_with(name="origin")
    mock_remote.fetch.assert_called_once_with()

    # The remote head was checked out.
    mock_remote_head.checkout.assert_called_once_with()

    # App's config template hasn't changed
    assert (
        myapp.template
        == "https://github.com/beeware/briefcase-tester-dummy-template.git"
    )

    # Cookiecutter was invoked with the path to the *cached* template name
    create_command.cookiecutter.assert_called_once_with(
        os.fsdecode(Path.home() / ".cookiecutters" / "briefcase-tester-dummy-template"),
        no_input=True,
        checkout="v37.42.7",
        output_dir=os.fsdecode(create_command.platform_path),
        extra_context=full_context,
    )


def test_cached_template_offline(
    monkeypatch, create_command, myapp, full_context, capsys
):
    """If the user is offline, a cached template won't be updated, but will
    still work."""
    # Set the Briefcase version
    monkeypatch.setattr(briefcase, "__version__", "37.42.7")

    mock_repo = mock.MagicMock()
    mock_remote = mock.MagicMock()
    mock_remote_head = mock.MagicMock()

    # Git returns a Repo, that repo can return a remote, and it has
    # heads that can be accessed. However, calling fetch on the remote
    # will cause a git error (error code 128).
    create_command.git.Repo.return_value = mock_repo
    mock_repo.remote.return_value = mock_remote
    mock_remote.refs.__getitem__.return_value = mock_remote_head
    mock_remote.fetch.side_effect = git_exceptions.GitCommandError("git", 128)

    # Generate the template.
    create_command.generate_app_template(myapp)

    # An attempt to fetch the repo origin was made
    mock_repo.remote.assert_called_once_with(name="origin")
    mock_remote.fetch.assert_called_once_with()

    # A warning was raised to the user about the fetch problem
    output = capsys.readouterr().out
    assert "** WARNING: Unable to update template" in output

    # The remote head was checked out.
    mock_remote_head.checkout.assert_called_once_with()

    # App's config template hasn't changed
    assert (
        myapp.template
        == "https://github.com/beeware/briefcase-tester-dummy-template.git"
    )

    # Cookiecutter was invoked with the path to the *cached* template name
    create_command.cookiecutter.assert_called_once_with(
        os.fsdecode(Path.home() / ".cookiecutters" / "briefcase-tester-dummy-template"),
        no_input=True,
        checkout="v37.42.7",
        output_dir=os.fsdecode(create_command.platform_path),
        extra_context=full_context,
    )


def test_cached_missing_branch_template(
    monkeypatch, create_command, myapp, full_context
):
    """If the cached repo doesn't have a branch for this Briefcase version, an
    error is raised."""
    # Set the Briefcase version
    monkeypatch.setattr(briefcase, "__version__", "37.42.7")

    mock_repo = mock.MagicMock()
    mock_remote = mock.MagicMock()

    # Git returns a Repo, that repo can return a remote. However, it doesn't
    # have a head corresponding to the requested Python version, so it
    # raises an IndexError
    create_command.git.Repo.return_value = mock_repo
    mock_repo.remote.return_value = mock_remote
    mock_remote.refs.__getitem__.side_effect = IndexError

    # Generating the template under there conditions raises an error
    with pytest.raises(TemplateUnsupportedVersion):
        create_command.generate_app_template(myapp)
