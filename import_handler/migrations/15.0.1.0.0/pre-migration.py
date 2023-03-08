# � 2021 Tobias Zehntner
# � 2021 Niboo SRL (https://www.niboo.com/)
# License Other Proprietary


def migrate(cr, version):
    """
    Migration from v13
    """
    cr.execute(
        """
        UPDATE ir_module_module SET state = 'to remove' WHERE name = 'log';
        DELETE FROM import_file;
        DELETE FROM ir_model_data WHERE name IN ('model_import_file', 'model_import_logger_line') OR model IN ('import.file', 'import.logger.line') OR name IN ('res_config_settings_view_form_import');
        DELETE FROM ir_ui_view WHERE name = 'res.config.settings.view.form.import';
        DELETE FROM ir_cron WHERE ir_actions_server_id in (
            SELECT id FROM ir_act_server WHERE model_id in (
                SELECT id FROM ir_model WHERE model IN ('import.file', 'import.logger.line')
            )
        );
        DELETE FROM ir_act_server WHERE model_id in (
            SELECT id FROM ir_model WHERE model IN ('import.file', 'import.logger.line')
        );
        DELETE FROM ir_model WHERE model IN ('import.file', 'import.logger.line');
        DELETE FROM ir_logging;
        """
    )
