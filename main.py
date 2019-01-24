import time
import numpy as np
from scipy.io import loadmat
from sklearn.preprocessing import normalize
from sklearn.metrics import cohen_kappa_score
from keras.models import Model, load_model
from keras.layers import Input, LeakyReLU, Dense, Dropout, Conv1D, MaxPool1D, \
                         GlobalAvgPool1D, Flatten, BatchNormalization, \
                         Concatenate
from keras.optimizers import Adam
from keras.constraints import MinMaxNorm
from keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
from keras.utils import to_categorical

# Parameters
NUM_EPOCHS = 50
BATCH_SIZE = 5
LEARNING_RATE = 0.001
ALPHA = 0.05

def prepare_data():
    """
    Helper function to prepare and split data
    """
    # Load EEG signals
    X = np.hstack((np.array(loadmat('psg_db/slp01am.mat')['val'])[2][:997500],
                   np.array(loadmat('psg_db/slp01bm.mat')['val'])[2][:997500],
                   np.array(loadmat('psg_db/slp02am.mat')['val'])[2][:37500],
                   np.array(loadmat('psg_db/slp02am.mat')['val'])[2][52500:225000],
                   np.array(loadmat('psg_db/slp02am.mat')['val'])[2][232500:675000],
                   np.array(loadmat('psg_db/slp02am.mat')['val'])[2][690000:705000],
                   np.array(loadmat('psg_db/slp02am.mat')['val'])[2][712500:840000],
                   np.array(loadmat('psg_db/slp02am.mat')['val'])[2][847500:885000],
                   np.array(loadmat('psg_db/slp02am.mat')['val'])[2][892500:997500],
                   np.array(loadmat('psg_db/slp02bm.mat')['val'])[2][:697500],
                   np.array(loadmat('psg_db/slp02bm.mat')['val'])[2][705000:997500],
                   np.array(loadmat('psg_db/slp03m.mat')['val'])[2][:997500],
                   np.array(loadmat('psg_db/slp04m.mat')['val'])[2][:997500],
                   np.array(loadmat('psg_db/slp14m.mat')['val'])[2][45000:540000],
                   np.array(loadmat('psg_db/slp14m.mat')['val'])[2][547500:997500],
                   np.array(loadmat('psg_db/slp16m.mat')['val'])[2][195000:997500],
                   np.array(loadmat('psg_db/slp32m.mat')['val'])[2][:997500],
                   np.array(loadmat('psg_db/slp37m.mat')['val'])[2][15000:997500],
                   np.array(loadmat('psg_db/slp41m.mat')['val'])[2][:997500],
                   np.array(loadmat('psg_db/slp45m.mat')['val'])[2][:997500],
                   np.array(loadmat('psg_db/slp48m.mat')['val'])[2][:997500],
                   np.array(loadmat('psg_db/slp59m.mat')['val'])[2][165000:997500],
                   np.array(loadmat('psg_db/slp60m.mat')['val'])[2][:997500],
                   np.array(loadmat('psg_db/slp61m.mat')['val'])[2][150000:997500],
                   np.array(loadmat('psg_db/slp66m.mat')['val'])[2][:997500],
                   np.array(loadmat('psg_db/slp67xm.mat')['val'])[2][:997500]))
    #M = 2313
    #X = np.reshape(X, (M, 7500))
    print(len(X)/7500)
    # Load annotations as labels
    annotations = open('psg_db/annotations.txt').readlines()
    Y = []

    for i in range(M):
        stage = annotations[i].split('\t')[1][0]
        if stage == 'W':
            stage = 0;
        elif stage == 'R':
            stage = 5
        else:
            stage = int(stage)
        Y.append(stage)

    Y = to_categorical(Y)

    # Shuffle data
    data = np.hstack((X,Y))
    np.random.shuffle(data)
    X = data[:, :7500]
    Y = data[:, 7500:]

    # Split data
    N = int(0.7*M)
    x_train = np.expand_dims(X[:N], axis=2)
    y_train = Y[:N]
    x_test = np.expand_dims(X[N:], axis=2)
    y_test = Y[N:]

    return x_train, y_train, x_test, y_test

def network(input_shape):
    """
    Network Architecture
    """
    # Normalization
    input = Input(shape=input_shape)
    norm = BatchNormalization(input_shape=input_shape, center=False, scale=True)(input)
    # Convolution Branch 1
    a = Conv1D(filters=32, kernel_size=20)(norm)
    a = LeakyReLU(alpha=ALPHA)(a)
    a = Conv1D(filters=32, kernel_size=20)(a)
    a = LeakyReLU(alpha=ALPHA)(a)
    a = MaxPool1D(pool_size=2)(a)
    a = Dropout(0.2)(a)
    # Convolution Branch 2
    b = Conv1D(filters=32, kernel_size=10)(norm)
    b = LeakyReLU(alpha=ALPHA)(b)
    b = Conv1D(filters=32, kernel_size=10)(b)
    b = LeakyReLU(alpha=ALPHA)(b)
    b = MaxPool1D(pool_size=2)(b)
    b = Dropout(0.2)(b)
    # Convolution Branch 3
    c = Conv1D(filters=32, kernel_size=5)(norm)
    c = LeakyReLU(alpha=ALPHA)(c)
    c = Conv1D(filters=32, kernel_size=5)(c)
    c = LeakyReLU(alpha=ALPHA)(c)
    c = MaxPool1D(pool_size=2)(c)
    c = Dropout(0.2)(c)
    # Concatenate branches and pool
    x = Concatenate(axis=1)([a,b,c])
    x = GlobalAvgPool1D()(x)
    # Output
    output = Dense(5, activation='softmax')(x)

    model = Model(inputs=[input], outputs=[output])

    optimizer = Adam(lr=LEARNING_RATE)
    model.compile(optimizer=optimizer, loss='categorical_crossentropy', metrics=['accuracy'])

    return model

def train(x_train, y_train, x_test, y_test):
    """
    Helper function to train network
    """
    save_point = ModelCheckpoint(filepath='saved_models/psg_model.h5', monitor='val_loss', save_best_only=True)
    early_stop = EarlyStopping(monitor='val_loss', patience=20, verbose=1)
    reduce_lr = ReduceLROnPlateau(monitor='val_loss', factor=0.1, patience=5)
    callbacks = [save_point]

    clf = network(input_shape=(7500,1))
    clf.fit(x_train, y_train, epochs=NUM_EPOCHS, batch_size=BATCH_SIZE,
            validation_data=(x_test, y_test), shuffle=True, callbacks=callbacks)

if __name__ == "__main__":
    start = time.time()

    x,y,xt,yt = prepare_data()
"""
    train(x,y,xt,yt)

    print("\nFinished training in " + str(int(time.time()-start)) + " seconds.")

    classifier = load_model("saved_models/psg_model.h5")

    print("\nFinal evaluation over training samples")
    scores_train = classifier.evaluate(x, y, BATCH_SIZE)
    print("Loss: ", scores_train[0])
    print("Accuracy: ", scores_train[1])

    print("\nFinal evaluation over test samples")
    scores_test = classifier.evaluate(xt, yt, BATCH_SIZE)
    print("Loss: ", scores_test[0])
    print("Accuracy: ", scores_test[1])

    print("\nFinal evaluation over all samples")
    X = np.concatenate((x, xt), axis=0)
    Y = np.concatenate((y, yt), axis=0)
    scores_full = classifier.evaluate(X, Y, BATCH_SIZE)
    print("Loss: ", scores_full[0])
    print("Accuracy: ", scores_full[1])
"""
