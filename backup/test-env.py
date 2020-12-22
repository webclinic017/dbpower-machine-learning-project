from tensorflow.python.client import device_lib
import tensorflow as tf

print('Tensorflow Version: '+str(tf.__version__))
print('GPU NAME: ', [x.name for x in device_lib.list_local_devices()])
print('GPU SUPPORT: '+str(tf.test.is_built_with_gpu_support()))
print('CUDA SUPPORT: '+str(tf.test.is_built_with_cuda()))
print('XLA SUPPORT: '+str(tf.test.is_built_with_xla()))
print(tf.test.gpu_device_name())
print(tf.config.list_physical_devices('GPU'))

try:
    tf.debugging.set_log_device_placement(True)
    a = tf.constant([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
    b = tf.constant([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
    c = tf.matmul(a, b)
    print('success')
except RuntimeError as e:
    print('fail', e)
