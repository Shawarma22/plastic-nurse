#ifndef DSP_FILTERS_H
#define DSP_FILTERS_H

#include <stdint.h>

class DCRemovalFilter {
public:
    DCRemovalFilter(float alpha = 0.95f);
    float step(float input);
    float getDC() const;
    void reset();

private:
    float alpha;
    float prevInput;
    float prevOutput;
    float dcEstimate;
};

#endif
