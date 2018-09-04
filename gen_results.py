import math
import time
import configparser as cp
import sys


# return running cycles, mac operations, used lanes
def gen_phase (h_lanes, single_len, v_lanes):
    run_cycles = h_lanes + single_len + v_lanes
    macops = v_lanes * single_len * h_lanes
    isram_read = v_lanes * single_len
    fsram_read = h_lanes * single_len
    return run_cycles, macops, isram_read, fsram_read


def gen_sram_size(array_h, array_w, bw, if_h, if_w, filt_h, filt_w, filt_d, filt_n, stride, batch):

    filt_size = filt_h * filt_w * filt_d
    fsram_required = filt_size
    
    of_h, of_w = (if_h - filt_h) / stride + 1, (if_w - filt_w) / stride + 1
    lanes_per_layer = of_h
    v_folds = int(math.ceil (1.0 * batch * lanes_per_layer / array_h)) 
    isram_required = filt_w * if_h * filt_d * v_folds

    return fsram_required, isram_required

def gen_layer (layer_type,array_h, array_w, bw, if_h, if_w, filt_h, filt_w, filt_d, filt_n, stride, batch, filename, layer_id, next_filt_w, next_stride, macop_cost, isram_read_cost, fsram_read_cost, isram_write_cost, fsram_write_cost, dram_read_cost, dram_write_cost):
 

    f = open(filename,"a")

    layer_run_cycles = 0
    layer_energy = 0

    filt_size = filt_h * filt_w * filt_d
    of_h, of_w = (if_h - filt_h) / stride + 1, (if_w - filt_w) / stride + 1
    lanes_per_layer = of_h
    rounds = int(math.ceil (1.0 * filt_n / array_w))
    last_round_filt_n = filt_n % array_w
    v_folds = int(math.ceil (1.0 * batch * lanes_per_layer / array_h)) 
    #
    last_phase_lanes = batch * lanes_per_layer % array_h
    phases = v_folds * of_h

    print (layer_id + ":rounds " + str(rounds) + ", phases " + str(phases))
    # running simulation
    # h_lanes for filt and v_lanes for ifmap
    for i in range(rounds):
        r_dram_read = r_dram_write = r_fsram_write = r_isram_write = r_macops = r_isram_read = r_fsram_read = r_run_cycles = r_fstalls = r_istalls = 0
        for k in range(v_folds):
            for l in range(of_h):
                j = k * of_h + l

                if i+1 == rounds and last_round_filt_n != 0:
                    h_lanes = last_round_filt_n
                else:
                    h_lanes = array_w

                if k+1 == v_folds and last_phase_lanes != 0:
                    v_lanes = last_phase_lanes
                else:
                    v_lanes = array_h

                #if j+1 ==  phases and last_phase_lanes != 0:
                #    v_lanes = last_phase_lanes
                #else:
                #    v_lanes = array_h

                #print("hv",h_lanes,v_lanes)

                run_cycles, macops, isram_read, fsram_read = gen_phase(h_lanes,filt_size,v_lanes)
                r_run_cycles += run_cycles
                if j != phases-1:
                    r_run_cycles -= h_lanes + v_lanes

                r_isram_read += isram_read 
                r_fsram_read += fsram_read 
                r_macops += macops
                # round == 0 read input feature
                if i == 0:
                    if j == 0:
                        input_load = v_lanes * filt_size
                    else:
                        if stride > filt_h:
                            print "error"
                        input_load = v_lanes * (filt_size / filt_h * stride)
                else:
                    input_load = 0
                # phase == 0 read filters 
                if j == 0:
                    filt_load = h_lanes * filt_size
                else:
                    filt_load = 0
                output_load = h_lanes * v_lanes
                istalls = 0 
                if input_load > 0 and layer_type == 0:
                    istalls += int(math.ceil(input_load*1.0/bw)) - (v_lanes+filt_size-bw/2)
                    r_istalls += int(math.ceil(input_load*1.0/bw)) - (v_lanes+filt_size-bw/2)
                fstalls = 0 
                if filt_load > 0:
                    fstalls += int(math.ceil(filt_load*1.0/bw)) - (h_lanes+filt_size-bw/2)
                    r_fstalls += int(math.ceil(filt_load*1.0/bw)) - (h_lanes+filt_size-bw/2)
                dram_read = filt_load
                r_dram_read += filt_load
                fsram_write = filt_load
                r_fsram_write += filt_load
                dram_write = 0
                if layer_type == 0:
                    # read from dram to isram
                    dram_read += input_load
                    r_dram_read += input_load
                    isram_write = input_load
                    r_isram_write += input_load
                    # write back result to isram
                    isram_write += output_load 
                    r_isram_write += int (output_load * (1.0 * next_filt_w / next_stride)) # consider reuse
                elif layer_type == 1:
                    # write back result to isram
                    isram_write = output_load 
                elif layer_type == 2:
                    # write back result to isram
                    isram_write = output_load 
                    r_isram_write += int (output_load * (1.0 * next_filt_w / next_stride)) # consider reuse
                    # write back result to dram 
                    r_isram_read += output_load 
                    dram_write += output_load
                    r_dram_write += output_load
                #print (run_cycles,macops,isram_read,fsram_read,input_load,filt_load,output_load)
                f.write(layer_id + "," + str(i) + "," + str(j) + "," + str(run_cycles) + "," + str(fstalls) + "," + str(istalls) + ","  + str(macops) + "," + str(isram_read) + "," + str(fsram_read) + "," + str(isram_write) + "," + str(fsram_write) + "," + str(dram_read) + "," + str(dram_write) + "," + str(h_lanes) + "," + str(v_lanes) + ",\n" )  
        f.write(",,,,,,,,,,,,,,,\n")
        '''
        print ('\tround:'+str(i+1))
        print ('\t\trun_cycles:'+str(r_run_cycles))
        print ('\t\tf_stalls:'+str(r_fstalls))
        print ('\t\ti_stalls:'+str(r_istalls))
        print ("\t\t=====================")
        print ('\t\tmacops:'+str(r_macops))
        print ("\t\t=====================")
        print ('\t\tisram_read:'+str(r_isram_read))
        print ('\t\tfsram_read:'+str(r_fsram_read))
        print ('\t\tisram_write:'+str(r_isram_write))
        print ('\t\tfsram_write:'+str(r_fsram_write))
        print ('\t\tdram_read:'+str(r_dram_read))
        print ('\t\tdram_write:'+str(r_dram_write))
        print ("\t\t=====================")
        '''

        r_energy = r_macops * macop_cost + r_isram_read * isram_read_cost + r_fsram_read * fsram_read_cost + r_isram_write * isram_write_cost + fsram_write * fsram_write_cost + r_dram_read * dram_read_cost + r_dram_write * dram_write_cost
        layer_energy += r_macops * macop_cost + r_isram_read * isram_read_cost + r_fsram_read * fsram_read_cost + r_isram_write * isram_write_cost + fsram_write * fsram_write_cost + r_dram_read * dram_read_cost + r_dram_write * dram_write_cost
        #energy += r_macops * macop_cost 

        f.write(layer_id + "," + str(i) + "," + "total" + "," + str(r_run_cycles) + "," + str(r_fstalls) + "," + str(r_istalls) + ","  + str(r_macops) + "," + str(r_isram_read) + "," + str(r_fsram_read) + "," + str(r_isram_write) + "," + str(r_fsram_write) + "," + str(r_dram_read) + "," + str(r_dram_write) + ",,," + str(r_energy) + ",\n" )  
        f.write(",,,,,,,,,,,,,,,\n")


        layer_run_cycles += r_run_cycles
    f.close()

    return layer_run_cycles, layer_energy

def parse_config(filename):
    # read info from file
    general = 'general' 
    arch_sec = 'architecture_presets'
    net_sec  = 'network_presets'

    config = cp.ConfigParser()
    config.read(filename)

    run_name = config.get(general, 'run_name')

    # ArrayHeight and ArrayWidth 
    ar_h = config.get(arch_sec, 'ArrayHeight').split(',')
    array_h = (int)(ar_h[0].strip())
    ar_w = config.get(arch_sec, 'ArrayWidth').split(',')
    array_w = (int)(ar_w[0].strip())

    dataflow= config.get(arch_sec, 'Dataflow')

    # architecture maximum bandwidth limitation
    arc_max_bandw = config.get(arch_sec,'maxbandwidth').split(',')
    bw = (int)(arc_max_bandw[0].strip())

    ## Read network_presets
    topology_file = config.get(net_sec, 'TopologyCsvLoc')
    topology_file = topology_file.split('"')[1]     #Config reads the quotes as well 

    return run_name, array_h, array_w, dataflow, bw

def parse_network(filename):
    networks = [] 
    param_file = open(filename, 'r')
    first = True
    for row in param_file:
        if first:
            first = False
            continue
                
        elems = row.strip().split(',')
        
        # Do not continue if incomplete line
        if len(elems) < 9:
            continue

        name = elems[0]

        ifmap_h = int(elems[1])
        ifmap_w = int(elems[2])

        filt_h = int(elems[3])
        filt_w = int(elems[4])

        num_channels = int(elems[5])
        num_filters = int(elems[6])

        stride = int(elems[7])

        batch = int(elems[8])
        networks.append({"name":name,"ifmap_h":ifmap_h,"ifmap_w":ifmap_w,"filt_h":filt_h,"filt_w":filt_w,"num_channels":num_channels,"num_filters":num_filters,"stride":stride,"batch":batch})
    return networks

if __name__ == "__main__":

    run_name, array_h, array_w, dataflow, bw = parse_config("./scale.cfg")
    networks = parse_network("./test.csv")
    filename = run_name + ".csv"

    max_fsram = max_isram = 0
    f = open(filename,"w")
    f.write("layer, FSRAM required per lane (bytes), ISRAM required per lane (bytes),\n")

    for i in range(len(networks)):
        if_h = networks[i]["ifmap_h"]
        if_w = networks[i]["ifmap_w"]
        filt_h = networks[i]["filt_h"]
        filt_w = networks[i]["filt_w"]
        filt_d = networks[i]["num_channels"]
        filt_n = networks[i]["num_filters"]
        stride = networks[i]["stride"]
        batch = networks[i]["batch"]
        layer_id = networks[i]["name"]
        if i < len(networks) - 1:
            next_filt_w = networks[i+1]["filt_w"]
            next_stride = networks[i+1]["stride"]
        else:
            next_filt_w = next_stride = -1 
        fsram, isram = gen_sram_size(array_h, array_w, bw, if_h, if_w, filt_h, filt_w, filt_d, filt_n, stride, batch)
        max_fsram = max(max_fsram,fsram)
        max_isram = max(max_isram,isram)
        f.write(layer_id+","+str(fsram)+","+str(isram)+",\n")

    f.write("max"+","+str(max_fsram)+","+str(max_isram)+",\n\n\n")
    f.write("layer,round,phase,run cycles,filter stalls,IF stalls,MACops,ISRAM read (bytes),FSRAM read (bytes),ISRAM write (bytes),FSRAM write (bytes),DRAM read (bytes), DRAM write (bytes),h lanes, v lanes, energy (pJ),\n" )
    f.close()
    
    macop_cost = 0.4

    # from 196608
    ss = [3072,6144,12288,24576,49152,98304,196608,393216,786432]
    isram_read_costs = {3072:3.92355,6144:5.02445,12288:6.99487,24576:12.693,49152:13.4342,98304:15.1876,196608:16.6383,393216:17.4039,786432:19.7384}
    isram_write_costs = {3072:2.42798,6144:2.72598,12288:3.09058,24576:4.74234,49152:5.48353,98304:7.2369,196608:8.23304,393216:13.0546,786432:15.8341}
    dram_read_cost, dram_write_cost = 100.0, 100.0 

    isram_read_cost = fsram_read_cost = -1
    # SRAM requirement
    for s in ss: 
        if s >= max_isram:
            isram_read_cost = isram_read_costs[s] 
            isram_write_cost = isram_write_costs[s] 
            break
    for s in ss: 
        if s >= max_fsram:
            fsram_read_cost = isram_read_costs[s] 
            fsram_write_cost = isram_write_costs[s] 
            break
    if isram_read_cost == -1 or fsram_read_cost == -1:
        print "One of the memory requirement is too large!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        sys.exit()

    for i in range(len(networks)):
        if_h = networks[i]["ifmap_h"]
        if_w = networks[i]["ifmap_w"]
        filt_h = networks[i]["filt_h"]
        filt_w = networks[i]["filt_w"]
        filt_d = networks[i]["num_channels"]
        filt_n = networks[i]["num_filters"]
        stride = networks[i]["stride"]
        batch = networks[i]["batch"]
        layer_id = networks[i]["name"]
        if i < len(networks) - 1:
            next_filt_w = networks[i+1]["filt_w"]
            next_stride = networks[i+1]["stride"]
        else:
            next_filt_w = next_stride = -1 

        if i == 0:
            gen_layer(0,array_h,array_w,bw,if_h,if_w,filt_h,filt_w,filt_d,filt_n,stride,batch,filename,layer_id,next_filt_w,next_stride, macop_cost, isram_read_cost, fsram_read_cost, isram_write_cost, fsram_write_cost, dram_read_cost, dram_write_cost)
        elif i == len(networks) - 1:
            gen_layer(2,array_h,array_w,bw,if_h,if_w,filt_h,filt_w,filt_d,filt_n,stride,batch,filename,layer_id,next_filt_w,next_stride, macop_cost, isram_read_cost, fsram_read_cost, isram_write_cost, fsram_write_cost, dram_read_cost, dram_write_cost)
        else:
            gen_layer(1,array_h,array_w,bw,if_h,if_w,filt_h,filt_w,filt_d,filt_n,stride,batch,filename,layer_id,next_filt_w,next_stride, macop_cost, isram_read_cost, fsram_read_cost, isram_write_cost, fsram_write_cost, dram_read_cost, dram_write_cost)
