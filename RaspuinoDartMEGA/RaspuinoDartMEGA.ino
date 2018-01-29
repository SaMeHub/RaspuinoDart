#define arr_len( x )  ( sizeof( x ) / sizeof( *x ) )

int outpins[] = {23, 25, 27, 29, 31, 33, 35};
int inpins[] = {22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44};

void setup() {
  Serial.begin(115200);
  for (int i = 0; i < arr_len(outpins); ++i) {
    pinMode(outpins[i], OUTPUT);
    digitalWrite(outpins[i], HIGH);
  }

  for (int i = 0; i < arr_len(inpins); ++i) {
    pinMode(inpins[i], INPUT);
    digitalWrite(inpins[i], HIGH);
  }
}

void loop() {
  for (int out = 0; out < arr_len(outpins); ++out) {
    digitalWrite(outpins[out], LOW);
    for (int in = 0; in < arr_len(inpins); ++in) {
      if (!digitalRead(inpins[in])) {
        Serial.write((out << 4) + in);
        digitalWrite(13, LOW);
        delay(250);
        digitalWrite(13, HIGH);
        delay(500);
      }
    }
    digitalWrite(outpins[out], HIGH);
  }
}

