import json
import uvicorn
import os
import gc
import numpy as np
import datetime
import tensorflow as tf
from tensorflow.core.protobuf import rewriter_config_pb2
from starlette.applications import Starlette
from starlette.responses import JSONResponse

import src.model as model
import src.sample as sample
import src.encoder as encoder

"""
Interactively run the model
:model_name=124M : String, which model to use
:seed=None : Integer seed for random number generators, fix seed to reproduce
    results
:nsamples=1 : Number of samples to return total
:batch_size=1 : Number of batches (only affects speed/memory).  Must divide nsamples.
:length=None : Number of tokens in generated text, if None (default), is
    determined by model hyperparameters
:temperature=1 : Float value controlling randomness in boltzmann
    distribution. Lower temperature results in less random completions. As the
    temperature approaches zero, the model will become deterministic and
    repetitive. Higher temperature results in more random completions.
:top_k=0 : Integer value controlling diversity. 1 means only 1 word is
    considered for each step (token), resulting in deterministic completions,
    while 40 means 40 words are considered at each step. 0 (default) is a
    special setting meaning no restrictions. 40 generally is a good value.
    :models_dir : path to parent folder containing model subfolders
    (i.e. contains the <model_name> folder)
"""

class AgataBotGPT():

    def __init__(self):
        self.model_name = 'run1'
        self.models_dir = os.path.expanduser(os.path.expandvars('models'))
        self.enc = encoder.get_encoder(self.model_name, self.models_dir)
        self.seed = None
        self.nsamples = 1
        self.batch_size = 1
        self.length = 50
        self.temperature = 0.7
        self.top_p = 0.9
        self.top_k = 40

        self.interactions = 0
        
        self.config()

    def config(self):
        assert self.nsamples % self.batch_size == 0

        self.hparams = model.default_hparams()
        with open(os.path.join(self.models_dir, self.model_name, 'hparams.json')) as f:
            self.hparams.override_from_dict(json.load(f))

        if self.length is None:
            self.length = self.hparams.n_ctx // 2
        elif self.length > self.hparams.n_ctx:
            raise ValueError("Can't get samples longer than window size: %s" % self.hparams.n_ctx)

        self.sess = self.start_tf_sess()

        #self.context = tf.placeholder(tf.int32, [self.batch_size, None])
        self.context = tf.compat.v1.placeholder(tf.int32, [self.batch_size, None])
        np.random.seed(self.seed)
        #tf.set_random_seed(self.seed)
        tf.compat.v1.set_random_seed(self.seed)
        self.output = sample.sample_sequence(
            hparams=self.hparams, length=self.length,
            context=self.context,
            batch_size=self.batch_size,
            temperature=self.temperature, top_k=self.top_k, top_p=self.top_p
        )
        
        #self.saver = tf.train.Saver()
        self.saver = tf.compat.v1.train.Saver()
        self.ckpt = tf.train.latest_checkpoint(os.path.join(self.models_dir, self.model_name))
        self.saver.restore(self.sess, self.ckpt)

        #Preload and open libcuda libs...
        self.interact_model('What is your name?')

    def start_tf_sess(self):
        config = tf.compat.v1.ConfigProto()
        config.gpu_options.allow_growth = True
        config.graph_options.rewrite_options.layout_optimizer = rewriter_config_pb2.RewriterConfig.OFF
        # config.intra_op_parallelism_threads = 4
        # config.inter_op_parallelism_threads = 4
        #self.sess = tf.Session(graph=tf.Graph())
        return tf.compat.v1.Session(config=config)

    def reset_session(self):
        tf.compat.v1.reset_default_graph()
        self.sess.close()
        self.sess = start_tf_sess()

    def interact_model(self, question):
        if self.interactions == 10:
            self.reset_session()
            self.interactions = 0
            gc.collect()
            
        question = question.rstrip().strip()
        context_tokens = self.enc.encode(question)
        generated = 0
        for _ in range(self.nsamples // self.batch_size):
            out = self.sess.run(self.output, feed_dict={
                self.context: [context_tokens for _ in range(self.batch_size)]
            })[:, len(context_tokens):]
            for i in range(self.batch_size):
                generated += 1
                text = self.enc.decode(out[i]) #final output generated by the model
                return text.split("\n")[1]
        self.interactions += 1

class Conversation():

    def __init__(self):
        #self.base = "Hy!\nHey!\nWhat is your name?\nMy name is Agata. Can I help you?\nHello, who are you?\nI am an IA called Agata created by Cristian. How can I help you?\n"
        self.base = 'Hy!\nHey!\nWhat is your name?\nMy name is Agata. Can I help you?\nHello, who are you?\nI am an IA called Agata created by Cristian. How can I help you?\nMy name is Agata and I am an artificial intelligence created by Cristian. I am created in the year 2021.\nI am a Deep Learning based robot. Above all I like classical music and Disney movies.\n'
        self.context = self.base
        self.timestamp = datetime.datetime.now()

    def reset_context():
        latest = self.context.split("\n")[-5:]
        self.context = self.base
        for l in latest:
            self.append_context(l)

    def append_context(self, plus):
        self.context += f'{plus}\n'
        if len(self.context) >= 10000:
            self.reset_context()

        timestamp_now = datetime.datetime.now()
        if timestamp_now > self.timestamp:
            td = timestamp_now - self.timestamp
        else:
            td = self.timestamp - timestamp_now
        td_mins = int(round(td.total_seconds() / 60))
        if td_mins > 10:
            self.reset_context()

    def __str__(self):
        return self.context