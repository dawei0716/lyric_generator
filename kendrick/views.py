from __future__ import absolute_import, division, print_function, unicode_literals
from django.shortcuts import render
from django.http import JsonResponse
from .models import GeneratedLyrics
import os
import tensorflow as tf
import time
import numpy as np
tf.enable_eager_execution()


path_to_file = "/Users/david/Desktop/django_ml_projects/lyric_gen/kendrick/lyrics.txt"
text = open(path_to_file, 'rb').read().decode(encoding='utf-8')
vocab = sorted(set(text))  # unique characters

# mapping from unique characters to indices
char2idx = {u: i for i, u in enumerate(vocab)}
# for indexing
idx2char = np.array(vocab)


# number of input examples to be processed together.
BATCH_SIZE = 64


vocab_size = len(vocab)

embedding_dim = 256
rnn_units = 1024


def build_model(vocab_size, embedding_dim, rnn_units, batch_size):
    model = tf.keras.Sequential([
        tf.keras.layers.Embedding(vocab_size, embedding_dim,
                                  batch_input_shape=[batch_size, None]),
        tf.keras.layers.GRU(rnn_units,
                            return_sequences=True,
                            stateful=True,
                            recurrent_initializer='glorot_uniform'),
        tf.keras.layers.Dense(vocab_size)
    ])
    return model


model = build_model(
    vocab_size=len(vocab),
    embedding_dim=embedding_dim,
    rnn_units=rnn_units,
    batch_size=BATCH_SIZE)


def loss(labels, logits):
    return tf.keras.losses.sparse_categorical_crossentropy(labels, logits, from_logits=True)


checkpoint_dir = './training_checkpoints'
checkpoint_prefix = os.path.join(checkpoint_dir, "ckpt_{epoch}")
checkpoint_callback = tf.keras.callbacks.ModelCheckpoint(
    filepath=checkpoint_prefix,
    save_weights_only=True)


model = build_model(vocab_size, embedding_dim, rnn_units, batch_size=1)
model.load_weights(
    '/Users/david/Desktop/django_ml_projects/lyric_gen/kendrick/training_checkpoints/ckpt_50')

# model.load_weights(tf.train.latest_checkpoint(checkpoint_dir))
model.build(tf.TensorShape([1, None]))


def generate_text(model, start_string, temperature, length):
    num_generate = int(length)

    input_eval = [char2idx[s] for s in start_string]
    input_eval = tf.expand_dims(input_eval, 0)

    text_generated = []
    temperature = float(temperature)
    model.reset_states()
    for i in range(num_generate):
        predictions = model(input_eval)
        predictions = tf.squeeze(predictions, 0)

        predictions = predictions / temperature
        predicted_id = tf.random.categorical(
            predictions, num_samples=1)[-1, 0].numpy()
        input_eval = tf.expand_dims([predicted_id], 0)

        text_generated.append(idx2char[predicted_id])

    return (start_string + ''.join(text_generated))


# Create your views here.


def about_page(request):
    return render(request, 'about.html')


def view_results(request):
    # # Submit prediction and show all
    data = {"dataset": GeneratedLyrics.objects.all()}
    return render(request, "results.html", data)


def kendrick(request):
    return render(request, 'kendrick.html')


def analyze_review(request):
    if request.POST.get('action') == 'post':
        seed = request.POST.get('seed').rstrip()
        temperature = request.POST.get('temperature').rstrip()
        length = request.POST.get('length').rstrip()
        lyrics = generate_text(model, start_string=seed,
                               temperature=temperature, length=length)

        GeneratedLyrics.objects.create(
            lyrics=lyrics, seed=seed, temperature=temperature, length=length)

        return JsonResponse({'lyrics': lyrics, 'seed': seed, 'temperature': temperature, 'length': length}, safe=False)
