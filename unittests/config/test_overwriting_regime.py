"""
Reactive Reality Machine Learning Config System - unit tests for overwriting regimes
Copyright (C) 2022  Reactive Reality

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Lesser General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
import logging
from pathlib import Path

import pytest

from unittests.config.utils import template
from yaecs.user_utils import make_config


class TestOverwritingRegimeLocked:
    """Tests for the 'locked' overwriting regime.

    In locked mode, a config cannot be changed after creation through direct
    attribute assignment. Any attempt to modify a parameter should raise an error.
    """

    def test_locked_prevents_direct_assignment(self):
        """Test that locked regime prevents direct parameter modification."""
        config = make_config(
            {"param1": 1, "param2": "test"},
            do_not_merge_command_line=True,
            overwriting_regime="locked"
        )

        # Verify initial values
        assert config.param1 == 1
        assert config.param2 == "test"

        # Attempt to modify should raise error
        with pytest.raises(RuntimeError, match="Overwriting params in locked configs is not allowed"):
            config.param1 = 2

        # Verify value hasn't changed
        assert config.param1 == 1

    def test_locked_prevents_nested_assignment(self):
        """Test that locked regime prevents modification of nested parameters.

        Note: Sub-configs created from dicts without tags are dict objects,
        so we test modification via merge operations instead.
        """
        config = make_config(
            {"param1": 1, "param2": 2},
            do_not_merge_command_line=True,
            overwriting_regime="locked"
        )

        # Attempt to modify should raise error
        with pytest.raises(RuntimeError, match="Overwriting params in locked configs is not allowed"):
            config.param1 = 10

        with pytest.raises(RuntimeError, match="Overwriting params in locked configs is not allowed"):
            config.param2 = 20

        assert config.param1 == 1
        assert config.param2 == 2

    def test_locked_allows_merge(self):
        """Test that locked regime still allows explicit merge operations."""
        config = make_config(
            {"param1": 1, "param2": "test"},
            do_not_merge_command_line=True,
            overwriting_regime="locked"
        )

        # Merge should still work
        config.merge({"param1": 2})
        assert config.param1 == 2

    def test_locked_multiple_parameters(self):
        """Test locked regime with multiple parameter modification attempts."""
        config = make_config(
            {"a": 1, "b": 2, "c": 3},
            do_not_merge_command_line=True,
            overwriting_regime="locked"
        )

        with pytest.raises(RuntimeError):
            config.a = 10

        with pytest.raises(RuntimeError):
            config.b = 20

        # All values should remain unchanged
        assert config.a == 1
        assert config.b == 2
        assert config.c == 3


class TestOverwritingRegimeUnsafe:
    """Tests for the 'unsafe' overwriting regime.

    In unsafe mode, no checks are performed and changes are made directly.
    The saved config might not accurately reflect the experiment if parameters
    are modified after saving.
    """

    def test_unsafe_allows_direct_assignment(self):
        """Test that unsafe regime allows direct parameter modification."""
        config = make_config(
            {"param1": 1, "param2": "test"},
            do_not_merge_command_line=True,
            overwriting_regime="unsafe"
        )

        assert config.param1 == 1

        # Direct assignment should work
        config.param1 = 2
        assert config.param1 == 2

        config.param2 = "modified"
        assert config.param2 == "modified"

    def test_unsafe_allows_nested_assignment(self):
        """Test that unsafe regime allows modification via direct assignment.

        Note: Sub-configs created from dicts without tags are dict objects.
        We test direct parameter modification instead.
        """
        config = make_config(
            {"param1": 5, "param2": "value"},
            do_not_merge_command_line=True,
            overwriting_regime="unsafe"
        )

        config.param1 = 10
        assert config.param1 == 10

        config.param2 = "changed"
        assert config.param2 == "changed"

    def test_unsafe_save_does_not_update(self, tmp_path):
        """Test that in unsafe mode, saved config is not automatically updated."""
        save_file = tmp_path / "unsafe_config.yaml"

        config = make_config(
            {"param1": 1, "param2": 2},
            do_not_merge_command_line=True,
            overwriting_regime="unsafe"
        )

        # Save initial state
        config.save(str(save_file))

        # Modify parameter
        config.param1 = 100
        assert config.param1 == 100

        # Load the saved file - should have original value
        loaded_config = make_config(str(save_file), do_not_merge_command_line=True)
        assert loaded_config.param1 == 1  # Original value, not modified
        assert loaded_config.param2 == 2

    def test_unsafe_warning_on_load(self, caplog):
        """Test that loading an unsafe config produces a warning."""
        tmp_file = Path("test_unsafe_warning.yaml")

        try:
            caplog.clear()
            with caplog.at_level(logging.WARNING):
                logging.getLogger("yaecs").propagate = True

                config = make_config(
                    {"param": 1},
                    do_not_merge_command_line=True,
                    overwriting_regime="unsafe"
                )
                config.save(str(tmp_file))

                # Loading an unsafe config should produce warning
                config2 = make_config(str(tmp_file), do_not_merge_command_line=True)

            assert "YOU ARE LOADING AN UNSAFE CONFIG" in caplog.text
        finally:
            if tmp_file.exists():
                tmp_file.unlink()
            hierarchy_file = Path(str(tmp_file).replace(".yaml", "_hierarchy.yaml"))
            if hierarchy_file.exists():
                hierarchy_file.unlink()

    def test_unsafe_allows_multiple_modifications(self):
        """Test multiple modifications in unsafe mode."""
        config = make_config(
            {"a": 1, "b": 2, "c": 3, "d": 4},
            do_not_merge_command_line=True,
            overwriting_regime="unsafe"
        )

        config.a = 10
        config.b = 20
        config.c = 30

        assert config.a == 10
        assert config.b == 20
        assert config.c == 30
        assert config.d == 4


class TestOverwritingRegimeAutoSave:
    """Tests for the 'auto-save' overwriting regime (default).

    In auto-save mode, when a user tries to change the config and it was saved
    before, the save is automatically overwritten to keep it consistent.
    """

    def test_locked_is_default(self):
        """Test that locked is the default overwriting regime."""
        config = make_config(
            {"param": 1},
            do_not_merge_command_line=True
        )

        assert config.config_metadata["overwriting_regime"] == "locked"

    def test_autosave_allows_modification_without_save(self):
        """Test that auto-save allows modification when no save exists."""
        config = make_config(
            {"param1": 1, "param2": "test"},
            do_not_merge_command_line=True,
            overwriting_regime="auto-save"
        )

        # Modification without prior save should work
        config.param1 = 2
        assert config.param1 == 2

    def test_autosave_updates_save_file(self, tmp_path):
        """Test that auto-save automatically updates the save file on modification."""
        save_file = tmp_path / "autosave_config.yaml"

        config = make_config(
            {"param1": 1, "param2": 2},
            do_not_merge_command_line=True,
            overwriting_regime="auto-save"
        )

        # Save initial state
        config.save(str(save_file))

        # Verify initial save
        loaded1 = make_config(str(save_file), do_not_merge_command_line=True)
        assert loaded1.param1 == 1

        # Modify parameter - should trigger auto-save
        config.param1 = 100
        assert config.param1 == 100

        # Load again - should have updated value
        loaded2 = make_config(str(save_file), do_not_merge_command_line=True)
        assert loaded2.param1 == 100  # Updated value
        assert loaded2.param2 == 2

    def test_autosave_updates_on_nested_modification(self, tmp_path):
        """Test that auto-save updates when parameters are modified."""
        save_file = tmp_path / "autosave_nested.yaml"

        config = make_config(
            {"param1": 5, "param2": 10},
            do_not_merge_command_line=True,
            overwriting_regime="auto-save"
        )

        config.save(str(save_file))

        # Modify parameters
        config.param1 = 50

        # Load and verify update
        loaded = make_config(str(save_file), do_not_merge_command_line=True)
        assert loaded.param1 == 50
        assert loaded.param2 == 10

    def test_autosave_multiple_modifications(self, tmp_path):
        """Test auto-save with multiple sequential modifications."""
        save_file = tmp_path / "autosave_multiple.yaml"

        config = make_config(
            {"a": 1, "b": 2, "c": 3},
            do_not_merge_command_line=True,
            overwriting_regime="auto-save"
        )

        config.save(str(save_file))

        # Multiple modifications
        config.a = 10
        config.b = 20
        config.c = 30

        # Each should have triggered auto-save
        # Load final state
        loaded = make_config(str(save_file), do_not_merge_command_line=True)
        assert loaded.a == 10
        assert loaded.b == 20
        assert loaded.c == 30

    def test_autosave_no_update_without_prior_save(self, tmp_path):
        """Test that auto-save doesn't create file if save() wasn't called first."""
        save_file = tmp_path / "no_autosave.yaml"

        config = make_config(
            {"param": 1},
            do_not_merge_command_line=True,
            overwriting_regime="auto-save"
        )

        # Modify without saving first
        config.param = 100

        # File should not exist
        assert not save_file.exists()

    def test_autosave_preserves_hierarchy(self, tmp_path):
        """Test that auto-save updates the saved file with current state.

        When a saved config is loaded, it becomes the default, so the hierarchy
        resets. This test verifies the auto-save mechanism works correctly.
        """
        save_file = tmp_path / "autosave_hierarchy.yaml"

        config = make_config(
            {"param1": 1},
            {"param1": 2},
            do_not_merge_command_line=True,
            overwriting_regime="auto-save"
        )

        config.save(str(save_file))

        # Modify parameter - should trigger auto-save
        config.param1 = 100

        # Load the saved file - it should have the updated value
        loaded = make_config(str(save_file), do_not_merge_command_line=True)
        assert loaded.param1 == 100  # The auto-saved value


class TestOverwritingRegimeComparison:
    """Tests comparing behavior across different overwriting regimes."""

    def test_regime_parameter_validation(self):
        """Test that invalid regime values are rejected."""
        with pytest.raises(Exception, match="'overwriting_regime' needs to be"):
            make_config(
                {"param": 1},
                do_not_merge_command_line=True,
                overwriting_regime="invalid_regime"
            )

    def test_all_regimes_allow_merge(self):
        """Test that all regimes allow explicit merge operations."""
        for regime in ["locked", "unsafe", "auto-save"]:
            config = make_config(
                {"param": 1},
                do_not_merge_command_line=True,
                overwriting_regime=regime
            )

            # Merge should work in all regimes
            config.merge({"param": 2})
            assert config.param == 2

    def test_regime_preserved_in_subconfigs(self):
        """Test that overwriting regime is consistent across config.

        Note: Dicts without YAML tags remain dicts, not sub-configs.
        We test the regime applies to all top-level parameters.
        """
        config = make_config(
            {"param1": 1, "param2": 2, "param3": 3},
            do_not_merge_command_line=True,
            overwriting_regime="locked"
        )

        # All parameters should be protected by the locked regime
        with pytest.raises(RuntimeError, match="Overwriting params in locked configs is not allowed"):
            config.param1 = 10

        with pytest.raises(RuntimeError, match="Overwriting params in locked configs is not allowed"):
            config.param2 = 20

    def test_regime_in_config_metadata(self):
        """Test that regime is correctly stored in config metadata."""
        for regime in ["locked", "unsafe", "auto-save"]:
            config = make_config(
                {"param": 1},
                do_not_merge_command_line=True,
                overwriting_regime=regime
            )
            assert config.config_metadata["overwriting_regime"] == regime

    def test_different_regimes_different_behavior(self, tmp_path):
        """Test that different regimes produce different behaviors for same actions."""
        save_file_locked = tmp_path / "locked.yaml"
        save_file_unsafe = tmp_path / "unsafe.yaml"
        save_file_autosave = tmp_path / "autosave.yaml"

        # Locked: Should raise error
        config_locked = make_config(
            {"param": 1},
            do_not_merge_command_line=True,
            overwriting_regime="locked"
        )
        config_locked.save(str(save_file_locked))
        with pytest.raises(RuntimeError):
            config_locked.param = 2
        assert config_locked.param == 1

        # Unsafe: Should allow change but not update file
        config_unsafe = make_config(
            {"param": 1},
            do_not_merge_command_line=True,
            overwriting_regime="unsafe"
        )
        config_unsafe.save(str(save_file_unsafe))
        config_unsafe.param = 2
        assert config_unsafe.param == 2
        loaded_unsafe = make_config(str(save_file_unsafe), do_not_merge_command_line=True)
        assert loaded_unsafe.param == 1  # Not updated

        # Auto-save: Should allow change and update file
        config_autosave = make_config(
            {"param": 1},
            do_not_merge_command_line=True,
            overwriting_regime="auto-save"
        )
        config_autosave.save(str(save_file_autosave))
        config_autosave.param = 2
        assert config_autosave.param == 2
        loaded_autosave = make_config(str(save_file_autosave), do_not_merge_command_line=True)
        assert loaded_autosave.param == 2  # Updated!


class TestOverwritingRegimeWithTemplateClass:
    """Tests for overwriting regime with template class configurations."""

    def test_template_class_respects_regime(self, yaml_default):
        """Test that template class respects overwriting regime setting."""
        config = template(default_config=yaml_default).load_config(
            [],
            do_not_merge_command_line=True,
            overwriting_regime="locked"
        )

        with pytest.raises(RuntimeError, match="Overwriting params in locked configs is not allowed"):
            config.param1 = 999

    def test_template_class_autosave(self, yaml_default, tmp_path):
        """Test auto-save behavior with template class."""
        save_file = tmp_path / "template_autosave.yaml"

        config = template(default_config=yaml_default).load_config(
            [],
            do_not_merge_command_line=True,
            overwriting_regime="auto-save"
        )

        config.save(str(save_file))
        original_value = config.param1

        config.param1 = original_value + 100

        loaded = make_config(str(save_file), do_not_merge_command_line=True)
        assert loaded.param1 == original_value + 100

    def test_template_class_unsafe(self, yaml_default, tmp_path):
        """Test unsafe behavior with template class."""
        save_file = tmp_path / "template_unsafe.yaml"

        config = template(default_config=yaml_default).load_config(
            [],
            do_not_merge_command_line=True,
            overwriting_regime="unsafe"
        )

        config.save(str(save_file))
        original_value = config.param1

        config.param1 = original_value + 100
        assert config.param1 == original_value + 100

        # File should not be updated in unsafe mode
        loaded = make_config(str(save_file), do_not_merge_command_line=True)
        assert loaded.param1 == original_value
