// Minimal QNN graph smoke test: two uint8 inputs -> ElementWiseAdd -> uint8 output.
#include <QnnInterface.h>
#include <QnnOpDef.h>
#include <HTP/QnnHtpDevice.h>
#include <dlfcn.h>
#include <cstdarg>
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <stdexcept>
#include <string>
#include <fstream>

static void logMessage(const char* fmt, QnnLog_Level_t level, uint64_t, va_list args) {
  fprintf(stderr, "QNN_LOG[%d] ", (int)level); vfprintf(stderr, fmt, args); fputc('\n', stderr);
}
static void check(Qnn_ErrorHandle_t e,const char* stage) {
  printf("STAGE %s status=%llu\n",stage,(unsigned long long)e); fflush(stdout);
  if(e!=QNN_SUCCESS)throw std::runtime_error(stage);
}
static Qnn_Tensor_t tensor(const char* name,Qnn_TensorType_t type,uint32_t* dims,uint8_t* data) {
  Qnn_Tensor_t t=QNN_TENSOR_INIT;
  t.v1.name=name; t.v1.type=type; t.v1.dataFormat=QNN_TENSOR_DATA_FORMAT_FLAT_BUFFER;
  t.v1.dataType=QNN_DATATYPE_UFIXED_POINT_8;
  t.v1.quantizeParams.encodingDefinition=QNN_DEFINITION_DEFINED;
  t.v1.quantizeParams.quantizationEncoding=QNN_QUANTIZATION_ENCODING_SCALE_OFFSET;
  t.v1.quantizeParams.scaleOffsetEncoding.scale=1.0f;
  t.v1.quantizeParams.scaleOffsetEncoding.offset=0;
  t.v1.rank=4;t.v1.dimensions=dims;t.v1.memType=QNN_TENSORMEMTYPE_RAW;
  t.v1.clientBuf.data=nullptr;t.v1.clientBuf.dataSize=0;
  return t;
}
int main(int argc,char** argv) {
  if(argc!=2){fprintf(stderr,"Use an absolute backend library path\n");return 64;}
  void* so=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);
  if(!so){fprintf(stderr,"DLOPEN_ERROR %s\n",dlerror());return 1;}
  const QnnInterface_t** providers=nullptr;uint32_t count=0;
  auto getProviders=(Qnn_ErrorHandle_t(*)(const QnnInterface_t***,uint32_t*))dlsym(so,"QnnInterface_getProviders");
  if(!getProviders || getProviders(&providers,&count)!=QNN_SUCCESS || !count)return 2;
  auto q=providers[0]->QNN_INTERFACE_VER_NAME;
  Qnn_LogHandle_t logger=nullptr;Qnn_BackendHandle_t backend=nullptr;
  Qnn_DeviceHandle_t device=nullptr;Qnn_ContextHandle_t context=nullptr;Qnn_ProfileHandle_t profile=nullptr;
  const bool htp=strstr(argv[1],"Htp")!=nullptr;int result=1;
  try {
    printf("BACKEND %s provider=%s backend_id=%u\n",argv[1],providers[0]->providerName?providers[0]->providerName:"",providers[0]->backendId);
    const char* build=nullptr;
    if(q.backendGetBuildId && q.backendGetBuildId(&build)==QNN_SUCCESS)printf("BACKEND_BUILD %s\n",build?build:"");
    check(q.logCreate(logMessage,QNN_LOG_LEVEL_INFO,&logger),"logCreate");
    check(q.backendCreate(logger,nullptr,&backend),"backendCreate");
    if(htp){
      QnnHtpDevice_CustomConfig_t custom={};
      custom.option=QNN_HTP_DEVICE_CONFIG_OPTION_SIGNEDPD;
      custom.useSignedProcessDomain.deviceId=0;
      custom.useSignedProcessDomain.useSignedProcessDomain=false;
      QnnDevice_Config_t cfg=QNN_DEVICE_CONFIG_INIT;
      cfg.option=QNN_DEVICE_CONFIG_OPTION_CUSTOM;cfg.customConfig=&custom;
      const QnnDevice_Config_t* configs[]={&cfg,nullptr};
      check(q.deviceCreate(logger,configs,&device),"deviceCreateUnsigned");
    }
    check(q.contextCreate(backend,device,nullptr,&context),"contextCreate");
    check(q.profileCreate(backend,QNN_PROFILE_LEVEL_BASIC,&profile),"profileCreate");
    Qnn_GraphHandle_t graph=nullptr;
    check(q.graphCreate(context,"isolated_add_uint8",nullptr,&graph),"graphCreate");
    uint32_t dims[]={1,1,1,4};
    uint8_t a[]={1,2,3,4},b[]={10,20,30,40},y[]={0,0,0,0};
    Qnn_Tensor_t in[]={tensor("input_a",QNN_TENSOR_TYPE_APP_WRITE,dims,a),tensor("input_b",QNN_TENSOR_TYPE_APP_WRITE,dims,b)};
    Qnn_Tensor_t out[]={tensor("output_y",QNN_TENSOR_TYPE_APP_READ,dims,y)};
    check(q.tensorCreateGraphTensor(graph,&in[0]),"input_a");
    check(q.tensorCreateGraphTensor(graph,&in[1]),"input_b");
    check(q.tensorCreateGraphTensor(graph,&out[0]),"output_y");
    Qnn_OpConfig_t op=QNN_OPCONFIG_INIT;
    op.v1.name="sum";op.v1.packageName="qti.aisw";op.v1.typeName=QNN_OP_ELEMENT_WISE_ADD;
    op.v1.numOfInputs=2;op.v1.inputTensors=in;op.v1.numOfOutputs=1;op.v1.outputTensors=out;
    check(q.graphAddNode(graph,op),"graphAddNode");
    check(q.graphFinalize(graph,profile,nullptr),"graphFinalize");
    in[0].v1.clientBuf.data=a;in[0].v1.clientBuf.dataSize=4;
    in[1].v1.clientBuf.data=b;in[1].v1.clientBuf.dataSize=4;
    out[0].v1.clientBuf.data=y;out[0].v1.clientBuf.dataSize=4;
    check(q.graphExecute(graph,in,2,out,1,profile,nullptr),"graphExecute");
    bool pass=y[0]==11 && y[1]==22 && y[2]==33 && y[3]==44;
    printf("GRAPH_RESULT={\"backend\":\"%s\",\"operation\":\"ElementWiseAdd\",\"input_a\":[1,2,3,4],\"input_b\":[10,20,30,40],\"output\":[%u,%u,%u,%u],\"expected\":[11,22,33,44],\"pass\":%s,\"cpu_fallback\":false}\n",htp?"HTP":"CPU",y[0],y[1],y[2],y[3],pass?"true":"false");
    const QnnProfile_EventId_t* ids=nullptr;uint32_t n=0;
    if(q.profileGetEvents(profile,&ids,&n)==QNN_SUCCESS){
      for(uint32_t i=0;i<n;i++){
        QnnProfile_EventData_t data=QNN_PROFILE_EVENT_DATA_INIT;
        if(q.profileGetEventData(ids[i],&data)==QNN_SUCCESS)printf("PROFILE type=%u unit=%u value=%llu name=%s\n",data.type,data.unit,(unsigned long long)data.value,data.identifier?data.identifier:"");
        const QnnProfile_EventId_t* sub=nullptr;uint32_t ns=0;
        if(q.profileGetSubEvents(ids[i],&sub,&ns)==QNN_SUCCESS)for(uint32_t j=0;j<ns;j++){
          data=QNN_PROFILE_EVENT_DATA_INIT;
          if(q.profileGetEventData(sub[j],&data)==QNN_SUCCESS)printf("PROFILE_SUB type=%u unit=%u value=%llu name=%s\n",data.type,data.unit,(unsigned long long)data.value,data.identifier?data.identifier:"");
        }
      }
    }
    std::ifstream maps("/proc/self/maps");std::string line;
    while(std::getline(maps,line))if(line.find("libQnn")!=std::string::npos)printf("LOADED_LIBRARY %s\n",line.c_str());
    result=pass?0:3;
  }catch(const std::exception& e){fprintf(stderr,"GRAPH_FAILED %s\n",e.what());}
  if(context)check(q.contextFree(context,profile),"contextFree");
  if(profile)check(q.profileFree(profile),"profileFree");
  if(device)check(q.deviceFree(device),"deviceFree");
  if(backend)check(q.backendFree(backend),"backendFree");
  if(logger)check(q.logFree(logger),"logFree");
  dlclose(so);return result;
}

