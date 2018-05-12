from keras.callbacks import EarlyStopping, Callback

class _FBFCheckpoint(Callback):
    def __init__(self, metric='val_acc', save_best=False, save_path=None, best_val_acc_so_far=0.0, snifftest_max_epoch=0, snifftest_min_val_acc=-1.0,
                 progress_callback=None, show_progress=True, format_val_acc='{:1.10f}'):
        super().__init__()
        self.save_best = save_best
        self.save_path = save_path
        self.previous_best_val_acc = best_val_acc_so_far
        self.best_val_acc_so_far = best_val_acc_so_far
        self.current_epoch = 0
        self.current_epoch_val_acc = 0
        self.current_epoch_max_val_acc = 0
        self.is_best = False
        self.best_epoch = 0
        self.best_val_acc = 0
        self.full_log = []
        self.saved = False
        self.saved_at_epoch = 0
        self.saved_at_val_acc = 0
        self.snifftest_max_epoch = snifftest_max_epoch
        self.snifftest_min_val_acc = snifftest_min_val_acc
        self.progress_callback = progress_callback
        self.snifftest_failed = False
        self.show_progress = show_progress
        self.format_val_acc = format_val_acc
        self.metric = metric

    def on_epoch_end(self, epoch, logs=()):
        logs = logs or {}
        logs['epoch'] = epoch
        self.full_log.append(logs)
        self.saved_at_epoch = False
        self.is_best = False
        self.saved = False
        self.current_epoch = epoch
        self.current_epoch_val_acc = logs.get('val_acc')
        self.snifftest_failed = (self.current_epoch >= self.snifftest_max_epoch) and (
        self.snifftest_min_val_acc >= self.current_epoch_val_acc)
        self.model.stop_training = self.snifftest_failed

        if self.snifftest_failed == False:
            if self.current_epoch_val_acc > self.best_val_acc:
                self.best_val_acc = self.current_epoch_val_acc
                self.best_epoch = epoch
                self.is_best = True

                if self.best_val_acc > self.best_val_acc_so_far:
                    self.previous_best_val_acc = self.best_val_acc_so_far
                    self.best_val_acc_so_far = self.best_val_acc

                    #save model structure as .json and weights as .hdf5 only if snifftest has passed
                    if (self.current_epoch >= self.snifftest_max_epoch):
                        if self.save_best:
                            self.saved = True
                            self.saved_at_epoch = self.best_epoch
                            self.saved_at_val_acc = self.best_val_acc
                            model_json = self.model.to_json()
                            with open(self.save_path + '.json', "w") as json_file:
                                json_file.write(model_json)
                            self.model.save_weights(self.save_path + '.hdf5')

        if self.show_progress:
            cva = self.format_val_acc.format(self.current_epoch_val_acc)
            bsf = self.format_val_acc.format(self.best_val_acc_so_far)
            is_best_so_far = self.is_best and (self.best_val_acc_so_far > self.previous_best_val_acc)
            flags = '  '
            msg = ''
            if self.is_best:
                flags = '* '
            if is_best_so_far:
                flags = '*!'
            if self.saved:
                msg = ' Saved '
            if self.snifftest_failed:
                msg = ' Snifftest failed '
            print(f'  e{self.current_epoch}: {self.metric}={cva} {flags} bsf={bsf} {msg}')


# -----------------------------------------------------------------------------------------------------------------------
def find_best_fit(
        model=None,
        metric='val_acc',
        xtrain=None,
        ytrain=None,
        xval=None,
        yval=None,
        shuffle=False,
        validation_split=0,
        batch_size=1000,
        epochs=2,
        patience=5,
        snifftest_max_epoch=0,
        snifftest_min_val_acc=0,
        show_progress=True,
        progress_val_acc_format='{:1.10f}',
        save_best=False,
        save_path=None,
        previous_best_val_acc=0,
        best_val_acc_so_far=0
        ):

    cbstopper = EarlyStopping(monitor='val_acc', patience=patience, verbose=0)
    cbcheckpoint = _FBFCheckpoint(save_best=save_best,
                                 save_path=save_path,
                                 metric=metric,
                                 best_val_acc_so_far=best_val_acc_so_far,
                                 snifftest_max_epoch=snifftest_max_epoch,
                                 snifftest_min_val_acc=snifftest_min_val_acc,
                                 show_progress=show_progress,
                                 format_val_acc=progress_val_acc_format)

    # call the native fit function
    if validation_split == 0:
        history = model.fit(xtrain, ytrain,
                            batch_size=batch_size,
                            epochs=epochs,
                            verbose=0,
                            callbacks=[cbcheckpoint, cbstopper],
                            shuffle=shuffle,
                            validation_data=[xval, yval])

    else:
        history = model.fit(xtrain, ytrain,
                            batch_size=batch_size,
                            epochs=epochs,
                            verbose=0,
                            callbacks=[cbcheckpoint, cbstopper],
                            shuffle=shuffle,
                            validation_split=validation_split)

    results = {}
    results['snifftest_failed'] = cbcheckpoint.snifftest_failed
    results['is_best'] = cbcheckpoint.is_best
    results['saved'] = cbcheckpoint.saved
    results['saved_at_epoch'] = cbcheckpoint.saved_at_epoch
    results['saved_at_val_acc'] = cbcheckpoint.saved_at_val_acc
    results['best_val_acc_so_far'] = cbcheckpoint.best_val_acc_so_far
    results['best_val_acc'] = cbcheckpoint.best_val_acc
    results['best_epoch'] = cbcheckpoint.best_epoch

    return results, cbcheckpoint.full_log
