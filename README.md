'El amor es la experiencia de que los otros no son otros. 
belleza es la experiencia de que los objetos no son objetos'. 
Rupert Spira 

    
interspecifics
# entrainment

Entrainment es un entorno performativo transmedial que revela estados de coherencia cardíaca en respuesta a la escucha activa y en tiempo real   
de los latidos del corazón humano. El performance presenta, en tres actos, a un grupo de participantes en el escenario, cada uno equipado   
con un monitor de variabilidad de la frecuencia cardíaca (HRV), mientras se  produce un proceso de biofeedback sonoro. El bucle evoluciona en  
ciclos de sincronía rítmica espontánea con los latidos del corazón de los participantes, dando forma a la pieza. Compuesta en vivo y de manera  
colaborativa, Entrainment presenta una sutil melodía que va del caos al unísono y viceversa.   

---
  
Entrainment is a transmedial performative environment that reveals states of cardiac coherence in response to active and real-time listening to human heartbeats. The performance, presented in three acts, features a group of participants on stage, each equipped with a heart rate variability (HRV) monitor, while a process of sound biofeedback occurs. The loop evolves in cycles of spontaneous rhythmic synchrony with the participants' heartbeats, shaping the piece. Composed live and collaboratively, Entrainment features a subtle melody that shifts from chaos to unison and back.

## Repository structure

##
[ECG_device] code, firmware, and specifications that needs to be uploaded to set the ECG device behavior which is basically 1) gather ECG sensor signal, 2) apply real time processing to the signal and 3) broadcast data to the audiovisual performance control mechanisms. 
Must be uploaded to the ESP32-S2-DevKit-C devices with custom ECG sensor adapters.

[signal_processing] python code to process the ECG signal for exploratory data analysis, peak detection, Heart Rate Variability and entrainment analysis.

[sound_interface] components for a sound interface in real time performative heart sensing.

![image](https://github.com/interspecifics/entrainment/assets/12953522/b424808c-a767-4a67-99a7-af5a44c6417a)

